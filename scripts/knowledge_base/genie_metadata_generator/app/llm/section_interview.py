"""
Generic Section-Based Interview Engine
Handles interviews for any template split into sections.
"""

import logging
from datetime import date, datetime
from pathlib import Path

import yaml
from llm.client import LLMClient

logger = logging.getLogger(__name__)


class SectionBasedInterview:
    """Generic section-by-section interview engine for any template."""

    def __init__(self, llm_client: LLMClient, template_config_path: Path, context_summarizer=None):
        """
        Initialize the section-based interview engine.

        Args:
            llm_client: LLMClient instance
            template_config_path: Path to sections.yaml config file
            context_summarizer: Optional ContextSummarizerService for large contexts
        """
        self.llm = llm_client
        self.config_path = template_config_path
        self.context_summarizer = context_summarizer

        # Load configuration with error handling
        try:
            with open(template_config_path) as f:
                self.config = yaml.safe_load(f)
        except FileNotFoundError:
            raise ValueError(f"Template config file not found: {template_config_path}") from None
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in template config: {e}") from e
        except Exception as e:
            raise ValueError(f"Failed to load template config: {e}") from e

        self.template_type = self.config['template_type']
        self.base_prompt_path = Path(template_config_path).parent.parent / self.config['base_prompt']
        self.template_dir = Path(template_config_path).parent
        self.sections = self.config['sections']

        # Interview state
        self.current_section_idx = 0
        self.completed_sections = {}
        self.conversation_history = []
        self.context_data = None
        self.skeleton_data = None

        # Planning state (Step 0)
        self.interview_plan = None
        self.pre_populated_yaml = None
        self.questions_needed = []
        self.planning_complete = False

        logger.info(f"Initialized SectionBasedInterview for {self.template_type} with {len(self.sections)} sections")

    def start_interview(self, context_data):
        """
        Start interview with initial context.

        This now runs Step 0 (Planning) first to pre-populate as much as possible,
        then only asks questions for fields that truly need human input.

        Args:
            context_data: Dict with table metadata or multi-table data

        Returns:
            Tuple of (planning_summary, first_question) or just first_question
        """
        self.context_data = context_data

        # Debug: Log profile status in received context_data
        if isinstance(context_data, list):
            # Multi-table (Genie)
            for table_data in context_data:
                table_name = f"{table_data.get('catalog', '?')}.{table_data.get('schema', '?')}.{table_data.get('table', '?')}"
                profile_summary = table_data.get('metadata', {}).get('profile_summary')
                if profile_summary:
                    logger.debug(f"Interview received {table_name} WITH profile ({len(profile_summary)} chars)")
                else:
                    logger.debug(f"Interview received {table_name} WITHOUT profile")
        else:
            # Single table
            table_name = f"{context_data.get('catalog', '?')}.{context_data.get('schema', '?')}.{context_data.get('table', '?')}"
            profile_summary = context_data.get('metadata', {}).get('profile_summary')
            if profile_summary:
                logger.debug(f"Interview received {table_name} WITH profile ({len(profile_summary)} chars)")
            else:
                logger.debug(f"Interview received {table_name} WITHOUT profile")

        # Generate skeleton (basic identifiers)
        self.skeleton_data = self._generate_skeleton(context_data)
        self.completed_sections['skeleton'] = self.skeleton_data

        logger.info(f"Starting interview for {self.template_type}, {len(self.sections)} sections")

        # Step 0: Generate interview plan (pre-populate + identify questions)
        self.interview_plan = self._generate_interview_plan(context_data)
        self.planning_complete = True

        # Store pre-populated content
        self.pre_populated_yaml = self._convert_plan_to_yaml(self.interview_plan)
        self.questions_needed = self.interview_plan.get('questions_needed', [])

        # Log planning results
        strategy = self.interview_plan.get('interview_strategy', {})
        logger.info(f"Planning complete: {len(self.questions_needed)} questions needed, "
                   f"estimated {strategy.get('estimated_time', 'unknown')}")

        # Start first section with context from planning
        return self._start_section(0)

    def get_planning_summary(self):
        """Get a summary of the planning results for UI display."""
        if not self.interview_plan:
            return None

        strategy = self.interview_plan.get('interview_strategy', {})
        questions = self.interview_plan.get('questions_needed', [])

        # Count pre-populated fields
        pre_pop = self.interview_plan.get('pre_populated', {})
        pre_pop_count = self._count_populated_fields(pre_pop)

        return {
            'pre_populated_count': pre_pop_count,
            'questions_count': len(questions),
            'estimated_time': strategy.get('estimated_time', '3-5 minutes'),
            'sections_to_skip': strategy.get('sections_to_skip', []),
            'focus_areas': strategy.get('focus_areas', []),
            'questions': questions
        }

    def _count_populated_fields(self, data, depth=0):
        """Recursively count populated fields in a dict."""
        if depth > 5:  # Prevent infinite recursion
            return 0

        count = 0
        if isinstance(data, dict):
            for _key, value in data.items():
                if value is not None and value != '' and value != []:
                    if isinstance(value, dict):
                        count += self._count_populated_fields(value, depth + 1)
                    else:
                        count += 1
        return count

    def _start_section(self, section_idx):
        """
        Start interview for a specific section.

        Uses planning data to provide context about what's pre-populated
        and what questions are needed.

        Args:
            section_idx: Index of section to start

        Returns:
            First question for this section
        """
        if section_idx >= len(self.sections):
            logger.info("All sections complete")
            return None  # All sections complete

        section_config = self.sections[section_idx]
        self.current_section_idx = section_idx

        logger.info(f"Starting section {section_idx + 1}/{len(self.sections)}: {section_config['name']}")

        # Load section-specific prompt and template
        section_prompt = self._load_section_prompt(section_config)
        section_template = self._load_section_template(section_config)

        # Build context including planning results
        lightweight_context = self._build_lightweight_context(section_config)

        # Add planning context if available
        planning_context = self._build_planning_context_for_section(section_config)

        # Fresh conversation history for this section
        self.conversation_history = [
            {"role": "system", "content": section_prompt},
            {
                "role": "user",
                "content": f"""Context for {section_config['name']}:

{lightweight_context}

{planning_context}

Template to populate:
```yaml
{section_template}
```

{section_config.get('prompt_focus', 'Please ask questions to populate this section.')}

IMPORTANT:
- Use the pre-populated values from the planning step as starting points
- Only ask questions for fields that truly need human confirmation
- Include inline answer suggestions based on the data profile
- Keep the interview efficient - aim for 1-3 questions maximum per section"""
            }
        ]

        try:
            response = self.llm.chat(self.conversation_history)
            self.conversation_history.append({"role": "assistant", "content": response})
            return response
        except Exception as e:
            logger.error(f"Failed to start section via LLM: {e}", exc_info=True)
            # Provide a fallback question based on section config
            fallback = f"Let's work on the {self.sections[self.current_section_idx]['name']} section. What information can you provide?"
            self.conversation_history.append({"role": "assistant", "content": fallback})
            return fallback

    def _build_planning_context_for_section(self, section_config):
        """Build planning context specific to this section."""
        if not self.interview_plan:
            return ""

        context_parts = []

        # Show pre-populated fields for this section
        pre_populated = self.interview_plan.get('pre_populated', {})
        if pre_populated:
            context_parts.append("## Pre-populated from Data Analysis (use these as starting points):\n")
            context_parts.append(f"```yaml\n{yaml.dump(pre_populated, default_flow_style=False)}\n```\n")

        # Show questions needed for this section
        questions = self.interview_plan.get('questions_needed', [])
        section_questions = [q for q in questions if q.get('section') == section_config['key']]

        if section_questions:
            context_parts.append("## Questions to Ask in This Section:\n")
            for q in section_questions:
                context_parts.append(f"- **{q['field']}**: {q.get('reason', 'Needs confirmation')}")
                if q.get('suggested_answer'):
                    context_parts.append(f"  - Suggested: {q['suggested_answer']}")
                context_parts.append("")
        else:
            context_parts.append("## This section may be largely pre-populated. Confirm the pre-populated values are correct.\n")

        return "\n".join(context_parts)

    def answer_question(self, user_answer):
        """
        Continue current section interview.

        Args:
            user_answer: User's response

        Returns:
            Next question or section completion message
        """
        self.conversation_history.append({"role": "user", "content": user_answer})

        # Trim history if needed (keep last 10 exchanges + system prompt)
        if len(self.conversation_history) > 22:  # system + 10 Q&A pairs
            trimmed = [self.conversation_history[0]] + self.conversation_history[-20:]
            logger.info(f"Trimmed conversation history from {len(self.conversation_history)} to {len(trimmed)} messages")
            self.conversation_history = trimmed

        try:
            response = self.llm.chat(self.conversation_history)
            self.conversation_history.append({"role": "assistant", "content": response})
            return response
        except Exception as e:
            logger.error(f"Failed to answer question via LLM: {e}", exc_info=True)
            # Re-raise to let the UI layer handle with appropriate error messages
            raise

    def complete_section(self, section_yaml=None):
        """
        Complete current section and move to next.

        Args:
            section_yaml: Optional YAML content for this section

        Returns:
            First question of next section, or None if all done
        """
        if section_yaml is None:
            # Extract from last response
            section_yaml = self._extract_yaml(self.conversation_history[-1]['content'])

        section_key = self.sections[self.current_section_idx]['key']
        self.completed_sections[section_key] = section_yaml

        logger.info(f"Completed section: {section_key}")

        self.current_section_idx += 1

        if self.current_section_idx < len(self.sections):
            return self._start_section(self.current_section_idx)
        else:
            logger.info("All sections completed")
            return None

    def skip_section(self):
        """
        Skip current section (use template defaults).

        Returns:
            First question of next section, or None if all done
        """
        section_key = self.sections[self.current_section_idx]['key']
        self.completed_sections[section_key] = None  # Skip marker

        logger.info(f"Skipped section: {section_key}")

        self.current_section_idx += 1

        if self.current_section_idx < len(self.sections):
            return self._start_section(self.current_section_idx)
        else:
            return None

    def get_merged_yaml(self):
        """
        Merge all completed sections into final YAML.

        Includes pre-populated data from planning step as the base.

        Returns:
            Complete YAML string
        """
        return self._merge_sections(self.completed_sections)

    def get_pre_populated_yaml(self):
        """Get the pre-populated YAML from planning (for early display)."""
        if not self.interview_plan:
            return self.skeleton_data or ""

        # Start with skeleton
        yaml_content = self.skeleton_data or ""

        # Add pre-populated content
        pre_populated = self.interview_plan.get('pre_populated', {})
        if pre_populated:
            yaml_content += "\n\n# Pre-populated from data analysis:\n"
            yaml_content += yaml.dump(pre_populated, default_flow_style=False, sort_keys=False)

        return yaml_content

    def restart_section(self, section_idx):
        """
        Restart a specific section (for editing).

        Args:
            section_idx: Index of section to restart

        Returns:
            First question for restarted section
        """
        logger.info(f"Restarting section {section_idx}: {self.sections[section_idx]['name']}")
        self.current_section_idx = section_idx
        return self._start_section(section_idx)

    def is_complete(self):
        """Check if interview is complete."""
        return self.current_section_idx >= len(self.sections)

    # Planning methods (Step 0)

    def _generate_interview_plan(self, context_data):
        """
        Step 0: Have LLM analyze data and create an interview plan.

        Uses template-specific prompts:
        - table_comment: interview_planning.md
        - genie_metadata: genie_interview_planning.md

        Args:
            context_data: Dict with table metadata and profile (or list for Genie)

        Returns:
            Dict with pre_populated yaml, questions_needed, and strategy
        """
        logger.info(f"Step 0: Generating interview plan for {self.template_type}...")

        # Select the right planning prompt based on template type
        planning_prompt = self._load_planning_prompt()

        # Build comprehensive context for planning
        full_context = self._build_full_context_for_planning(context_data)

        # Conditionally summarize if context is too large (using service)
        if self.context_summarizer:
            full_context = self.context_summarizer.summarize_if_needed(full_context, max_chars=8000)
        else:
            # Fallback: simple truncation if no summarizer service
            if len(full_context) > 8000:
                logger.warning(f"No context summarizer available, truncating {len(full_context)} chars to 8000")
                full_context = full_context[:8000] + "\n\n...(truncated)"

        # Load all section templates to show what needs to be populated
        all_templates = self._load_all_section_templates()

        # Build user message based on template type
        if self.template_type == 'genie_metadata':
            user_message = f"""Please analyze these tables and create an interview plan for the Genie space.

## Tables with Tier 1 YAMLs and Data Profiles

{full_context}

## Genie Template to Populate

```yaml
{all_templates}
```

Create a plan that:
1. Pre-populates SQL expressions, query instructions, and examples from the table data
2. Lists ONLY the questions that truly need human confirmation
3. Provides suggested answers based on the Tier 1 YAMLs

Output your plan in the specified YAML format."""
        else:
            user_message = f"""Please analyze this table and create an interview plan.

## Table Context and Data Profile

{full_context}

## Template to Populate

```yaml
{all_templates}
```

Create a plan that:
1. Pre-populates as many fields as possible from the data profile
2. Lists ONLY the questions that truly need human input
3. Provides suggested answers for each question

Output your plan in the specified YAML format."""

        planning_messages = [
            {"role": "system", "content": planning_prompt},
            {"role": "user", "content": user_message}
        ]

        # Log total planning input size for monitoring
        total_chars = len(planning_prompt) + len(user_message)
        logger.info(f"Planning prompt total size: {total_chars:,} chars (~{total_chars // 4:,} tokens)")
        logger.info(f"  - System prompt: {len(planning_prompt):,} chars")
        logger.info(f"  - User message (context + template): {len(user_message):,} chars")

        try:
            response = self.llm.chat(planning_messages)
            logger.info(f"Planning response length: {len(response)} chars")

            # Validate response is not empty
            if not response or not response.strip():
                logger.error("LLM returned empty planning response")
                raise ValueError("Empty response from LLM during planning")

            # Parse the planning response
            plan = self._parse_interview_plan(response)

            # Validate plan has content
            if not plan or (not plan.get('pre_populated') and not plan.get('questions')):
                logger.warning("Planning produced empty plan, using fallback")
                raise ValueError("Planning produced no useful content")

            return plan
        except Exception as e:
            logger.error(f"Failed to generate interview plan via LLM: {e}", exc_info=True)
            # Return a minimal fallback plan
            return {
                'pre_populated': {},
                'questions': [],
                'metadata': {'note': 'Planning failed, proceeding with manual interview'}
            }

    def _load_planning_prompt(self):
        """Load the appropriate planning prompt for this template type."""
        prompts_dir = self.template_dir.parent / 'prompts'

        # Try template-specific planning prompt first
        if self.template_type == 'genie_metadata':
            prompt_path = prompts_dir / 'genie_interview_planning.md'
        else:
            prompt_path = prompts_dir / 'interview_planning.md'

        if prompt_path.exists():
            with open(prompt_path) as f:
                return f.read()

        # Fallback to generic planning prompt
        generic_path = prompts_dir / 'interview_planning.md'
        if generic_path.exists():
            with open(generic_path) as f:
                return f.read()

        return self._get_default_planning_prompt()

    def _get_default_planning_prompt(self):
        """Return default planning prompt if file not found."""
        return """You are helping plan an efficient interview to document a database table.

Analyze the provided data and pre-populate as many template fields as possible.
Only ask questions for fields that truly require human knowledge.

Output format:
```yaml
pre_populated:
  # Fields you can fill from the data

questions_needed:
  - field: "field_name"
    section: "section_name"
    reason: "why human input needed"
    suggested_answer: "your best guess"

interview_strategy:
  total_questions: N
  estimated_time: "X minutes"
```"""

    def _build_full_context_for_planning(self, context_data):
        """Build comprehensive context for planning (includes full profile)."""
        if self.template_type == 'table_comment':
            return self._build_full_table_context(context_data)
        elif self.template_type == 'genie_metadata':
            return self._build_full_multi_table_context(context_data)
        return str(context_data)

    def _build_full_table_context(self, table_data):
        """Build full table context including complete profile for planning."""
        context = f"""## Table Information
- **Full Name**: {table_data['catalog']}.{table_data['schema']}.{table_data['table']}
- **Catalog**: {table_data['catalog']}
- **Schema**: {table_data['schema']}
- **Table**: {table_data['table']}
"""

        # Get metadata (may contain columns, existing_comment, etc.)
        metadata = table_data.get('metadata', {})

        # Add existing comment if any (check both locations)
        existing_comment = table_data.get('existing_comment') or metadata.get('existing_comment')
        if existing_comment:
            context += f"- **Existing Comment**: {existing_comment}\n"

        # Add row count (check both locations)
        row_count = table_data.get('row_count') or metadata.get('row_count')
        if row_count:
            context += f"- **Row Count**: {row_count:,}\n"

        # Add all columns with details (check both locations)
        columns = table_data.get('columns', []) or metadata.get('columns', [])
        context += f"\n## Columns ({len(columns)} total)\n\n"

        for col in columns:
            col_line = f"- **{col['name']}** (`{col['type']}`)"
            if not col.get('nullable', True):
                col_line += " NOT NULL"
            if col.get('comment'):
                col_line += f" - {col['comment']}"
            context += col_line + "\n"

        # Add FULL profile summary using utility function
        from utils.data_conversion import get_profile_summary
        profile_summary = get_profile_summary(table_data)

        if profile_summary:
            context += f"\n## Data Profile (from actual data analysis)\n\n{profile_summary}\n"
        else:
            context += "\n## Data Profile\n\n*No profile generated - recommend generating profile for better results*\n"

        return context

    def _build_full_multi_table_context(self, tables_data):
        """Build full multi-table context for Genie planning with complete profiles and YAMLs."""
        context = f"## Genie Space with {len(tables_data)} Tables\n\n"

        for idx, table_data in enumerate(tables_data, 1):
            table_name = f"{table_data['catalog']}.{table_data['schema']}.{table_data['table']}"
            context += f"### Table {idx}: {table_name}\n\n"

            # Include FULL Tier 1 YAML (contains business context, granularity, relationships)
            if table_data.get('tier1_yaml'):
                context += f"**Table Comment YAML (Tier 1):**\n```yaml\n{table_data['tier1_yaml']}\n```\n\n"

            # Include metadata and columns
            metadata = table_data.get('metadata', {})
            columns = metadata.get('columns', [])

            if columns:
                context += f"**Columns ({len(columns)} total):**\n"
                for col in columns[:30]:  # Show up to 30 columns
                    col_line = f"- {col['name']} ({col['type']})"
                    if col.get('comment'):
                        col_line += f" - {col['comment']}"
                    context += col_line + "\n"
                if len(columns) > 30:
                    context += f"- ... and {len(columns) - 30} more columns\n"
                context += "\n"

            # Include FULL data profile (critical for SQL expression generation)
            from utils.data_conversion import get_profile_summary

            # Debug: Log what's in table_data before extracting profile
            logger.debug(f"Building context for {table_name}, checking for profile...")
            logger.debug(f"  - Has 'metadata' key: {'metadata' in table_data}")
            if 'metadata' in table_data:
                logger.debug(f"  - Has 'profile_summary' in metadata: {'profile_summary' in table_data['metadata']}")

            profile_summary = get_profile_summary(table_data)

            if profile_summary:
                logger.info(f"Including data profile for {table_name} ({len(profile_summary)} chars)")
                context += f"**Data Profile:**\n{profile_summary}\n\n"
            else:
                logger.warning(f"No data profile available for {table_name}")
                context += "*No data profile available for this table*\n\n"

            context += "---\n\n"

        return context

    def _load_all_section_templates(self):
        """Load and combine all section templates."""
        all_templates = ""

        # Start with skeleton
        skeleton_path = self.template_dir / '00_skeleton.yml'
        if skeleton_path.exists():
            with open(skeleton_path) as f:
                all_templates += f"# === SKELETON ===\n{f.read()}\n\n"

        # Add each section
        for section in self.sections:
            template_path = self.template_dir / section['file']
            if template_path.exists():
                with open(template_path) as f:
                    all_templates += f"# === {section['name'].upper()} ===\n{f.read()}\n\n"

        return all_templates

    def _parse_interview_plan(self, response):
        """Parse the LLM's interview plan response."""
        plan = {
            'pre_populated': {},
            'questions_needed': [],
            'interview_strategy': {},
            'raw_response': response
        }

        # Extract YAML from response
        yaml_content = self._extract_yaml(response)

        if yaml_content:
            try:
                parsed = yaml.safe_load(yaml_content)
                if parsed:
                    plan['pre_populated'] = parsed.get('pre_populated', {})
                    plan['questions_needed'] = parsed.get('questions_needed', [])
                    plan['interview_strategy'] = parsed.get('interview_strategy', {})
                    logger.info(f"Parsed plan: {len(plan['questions_needed'])} questions needed")
            except yaml.YAMLError as e:
                logger.warning(f"Failed to parse planning YAML: {e}")
                # Try to extract pre_populated section at least
                plan['pre_populated'] = self._extract_pre_populated_from_response(response)
        else:
            logger.warning("No YAML block found in planning response")
            plan['pre_populated'] = self._extract_pre_populated_from_response(response)

        return plan

    def _extract_pre_populated_from_response(self, response):
        """Try to extract pre-populated content even without proper YAML structure."""
        # This is a fallback - try to find any useful content
        pre_populated = {}

        # Look for common fields in the response
        if 'description:' in response.lower():
            # Try to extract description
            lines = response.split('\n')
            for i, line in enumerate(lines):
                if 'description:' in line.lower() and '|' in line:
                    # Multi-line description
                    desc_lines = []
                    for j in range(i + 1, min(i + 10, len(lines))):
                        if lines[j].strip() and not any(k in lines[j].lower() for k in ['granularity:', 'business_']):
                            desc_lines.append(lines[j].strip())
                        else:
                            break
                    if desc_lines:
                        pre_populated['description'] = '\n'.join(desc_lines)
                    break

        return pre_populated

    def _convert_plan_to_yaml(self, plan):
        """Convert pre-populated plan data to YAML string."""
        if not plan.get('pre_populated'):
            return ""

        try:
            return yaml.dump(plan['pre_populated'], default_flow_style=False, sort_keys=False)
        except Exception as e:
            logger.error(f"Error converting plan to YAML: {e}")
            return ""

    # Helper methods

    def _generate_skeleton(self, context_data):
        """Generate basic skeleton YAML with identifiers."""
        skeleton_path = self.template_dir / '00_skeleton.yml'

        if not skeleton_path.exists():
            logger.warning(f"Skeleton template not found: {skeleton_path}")
            return ""

        with open(skeleton_path) as f:
            skeleton = f.read()

        # For table comments: populate table_identity
        if self.template_type == 'table_comment' and isinstance(context_data, dict):
            if 'catalog' in context_data:
                skeleton = skeleton.replace('catalog: "main"', f'catalog: "{context_data["catalog"]}"')
                skeleton = skeleton.replace('schema: "schema_name"', f'schema: "{context_data["schema"]}"')
                skeleton = skeleton.replace('name: "table_name"', f'name: "{context_data["table"]}"')
                skeleton = skeleton.replace('business_name: "Table Business Name"',
                                          f'business_name: "{context_data.get("table", "").title()}"')

        # For genie metadata: populate space_identity and table_identity
        elif self.template_type == 'genie_metadata' and isinstance(context_data, list):
            # Multi-table context - just use first table for identity
            if context_data:
                first_table = context_data[0]
                skeleton = skeleton.replace('catalog: "main"', f'catalog: "{first_table["catalog"]}"')
                skeleton = skeleton.replace('schema: "schema_name"', f'schema: "{first_table["schema"]}"')
                skeleton = skeleton.replace('name: "table_name"', f'name: "{first_table["table"]}"')

        return skeleton

    def _load_section_prompt(self, section_config):
        """Load section-specific prompt, or base prompt if not found."""
        # Try section-specific prompt first
        section_prompt_path = self.template_dir.parent / 'prompts' / f'{self.template_type}_sections' / f'{section_config["key"]}.md'

        if section_prompt_path.exists():
            with open(section_prompt_path) as f:
                return f.read()

        # Fall back to base prompt
        if self.base_prompt_path.exists():
            with open(self.base_prompt_path) as f:
                base_prompt = f.read()

            # Add section focus
            section_prompt = f"""{base_prompt}

## Current Section: {section_config['name']}

{section_config.get('description', '')}

Focus: {section_config.get('prompt_focus', 'Ask questions to populate this section.')}

Remember to include inline answer suggestions in your questions.
"""
            return section_prompt

        # Last resort: minimal prompt
        return f"""You are helping populate the {section_config['name']} section.

{section_config.get('description', '')}

{section_config.get('prompt_focus', 'Ask questions to populate this section.')}

Include inline answer suggestions in your questions."""

    def _load_section_template(self, section_config):
        """Load section template file."""
        template_path = self.template_dir / section_config['file']

        if not template_path.exists():
            logger.error(f"Section template not found: {template_path}")
            return f"# Template not found: {section_config['file']}"

        with open(template_path) as f:
            return f.read()

    def _build_lightweight_context(self, section_config):
        """Build minimal context for current section, including data from previous sections."""
        if not self.context_data:
            return "No context data available."

        context_parts = []

        # For table comments: show table summary (with FULL profile, no truncation)
        if self.template_type == 'table_comment':
            context_parts.append(self._build_table_context_summary(self.context_data))

        # For genie metadata: show multi-table summary (with FULL profiles, no truncation)
        elif self.template_type == 'genie_metadata':
            context_parts.append(self._build_multi_table_context_summary(self.context_data))

        # Add summary of previously completed sections to reduce repetitive questions
        previous_sections_summary = self._build_previous_sections_summary()
        if previous_sections_summary:
            context_parts.append(previous_sections_summary)

        context = "\n\n".join(context_parts) if context_parts else str(self.context_data)

        # Use context summarizer if available (like planning phase does)
        # Only triggers if context > 8000 chars, providing intelligent compression
        if self.context_summarizer:
            context = self.context_summarizer.summarize_if_needed(context, max_chars=8000)

        return context

    def _build_previous_sections_summary(self):
        """Build a summary of data gathered in previous sections."""
        if not self.completed_sections:
            return ""

        summary_parts = []

        for section_key, section_yaml in self.completed_sections.items():
            if not section_yaml or section_key == 'skeleton':
                continue

            # Find section name
            section_name = section_key
            for s in self.sections:
                if s['key'] == section_key:
                    section_name = s['name']
                    break

            # Extract key-value pairs from the YAML (simplified parsing)
            extracted_values = []
            lines = section_yaml.split('\n')

            for line in lines:
                # Skip empty lines and comments
                if not line.strip() or line.strip().startswith('#'):
                    continue

                # Look for simple key: value pairs
                if ':' in line and not line.strip().endswith(':'):
                    key_part = line.split(':')[0].strip()
                    value_part = ':'.join(line.split(':')[1:]).strip()

                    # Skip if value is empty or just a placeholder
                    if value_part and value_part not in ['""', "''", '|', '>']:
                        # Truncate long values
                        if len(value_part) > 100:
                            value_part = value_part[:100] + "..."
                        extracted_values.append(f"  - {key_part}: {value_part}")

            if extracted_values:
                summary_parts.append(f"**Previously gathered in {section_name}:**\n" + "\n".join(extracted_values[:10]))

        if summary_parts:
            return "---\n## Data Already Gathered (use these, don't re-ask):\n\n" + "\n\n".join(summary_parts)

        return ""

    def _build_table_context_summary(self, table_data):
        """Build lightweight table context (minimal column info)."""
        # Get metadata (may contain columns, profile, etc.)
        metadata = table_data.get('metadata', {})
        columns = table_data.get('columns', []) or metadata.get('columns', [])

        summary = f"""Table: {table_data['catalog']}.{table_data['schema']}.{table_data['table']}

Columns ({len(columns)}):
"""
        # Only show column names and types, not full details
        for col in columns[:20]:  # Limit to first 20
            summary += f"  - {col['name']}: {col['type']}\n"

        if len(columns) > 20:
            summary += f"  ... and {len(columns) - 20} more columns\n"

        # Add profile summary if available (check both locations)
        profile_summary = table_data.get('profile_summary') or metadata.get('profile_summary')
        if profile_summary:
            # Include FULL profile - context_summarizer will compress if needed
            summary += f"\nData Profile:\n{profile_summary}\n"

        return summary

    def _build_multi_table_context_summary(self, tables_data):
        """Build lightweight multi-table context."""
        summary = f"Tables in this Genie space: {len(tables_data)}\n\n"

        for idx, table_data in enumerate(tables_data, 1):
            summary += f"{idx}. {table_data['catalog']}.{table_data['schema']}.{table_data['table']}\n"
            summary += f"   Columns: {len(table_data.get('metadata', {}).get('columns', []))}\n"

            # Add tier1_yaml description if available
            if table_data.get('tier1_yaml'):
                # Extract description line
                for line in table_data['tier1_yaml'].split('\n')[:30]:
                    if 'description:' in line:
                        summary += f"   {line.strip()}\n"
                        break

            # Include profile summary for better Genie configuration
            from utils.data_conversion import get_profile_summary
            profile_summary = get_profile_summary(table_data)
            if profile_summary:
                # Include FULL profile - context_summarizer will compress if needed
                summary += f"   Data Profile: {profile_summary}\n"

            summary += "\n"

        return summary

    def _extract_yaml(self, response):
        """Extract YAML content from LLM response."""
        if "```yaml" not in response:
            return None

        lines = response.split("\n")
        in_yaml = False
        yaml_lines = []

        for line in lines:
            if line.strip().startswith("```yaml"):
                in_yaml = True
            elif line.strip() == "```" and in_yaml:
                break
            elif in_yaml:
                yaml_lines.append(line)

        return "\n".join(yaml_lines) if yaml_lines else None

    def _merge_sections(self, completed_sections):
        """Merge all sections into complete YAML."""
        # Start with skeleton
        merged = completed_sections.get('skeleton', '')

        # Add each completed section
        for section in self.sections:
            section_key = section['key']

            if section_key in completed_sections and completed_sections[section_key]:
                merged += "\n\n# " + "=" * 70 + "\n"
                merged += f"# {section['name'].upper()}\n"
                merged += "# " + "=" * 70 + "\n\n"
                merged += completed_sections[section_key]

        return merged

    # === Serialization Methods (for persistence) ===

    def to_dict(self) -> dict:
        """
        Serialize interview state to dict for persistence.

        This enables storing interview progress in a database and resuming later.
        The LLMClient is NOT serialized - it must be recreated on restore.

        Returns:
            Dict containing all serializable interview state
        """
        return {
            # Config (to recreate instance)
            'template_type': self.template_type,
            'config_path': str(self.config_path),

            # Interview progress state
            'current_section_idx': self.current_section_idx,
            'completed_sections': self.completed_sections,
            'conversation_history': self.conversation_history,

            # Context and planning data (sanitized for JSON)
            'context_data': self._sanitize_for_json(self.context_data),
            'skeleton_data': self.skeleton_data,
            'interview_plan': self._sanitize_for_json(self.interview_plan),
            'pre_populated_yaml': self.pre_populated_yaml,
            'questions_needed': self.questions_needed,
            'planning_complete': self.planning_complete,
        }

    def _sanitize_for_json(self, obj):
        """
        Recursively convert non-JSON-serializable objects to JSON-safe types.

        Handles:
        - datetime/date objects -> ISO format strings
        - Path objects -> strings
        - Nested dicts and lists

        Args:
            obj: Object to sanitize

        Returns:
            JSON-serializable version of obj
        """
        if obj is None:
            return None
        elif isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, Path):
            return str(obj)
        elif isinstance(obj, dict):
            return {k: self._sanitize_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._sanitize_for_json(item) for item in obj]
        else:
            return obj

    @classmethod
    def from_dict(cls, data: dict, llm_client: 'LLMClient', context_summarizer=None) -> 'SectionBasedInterview':
        """
        Restore interview from serialized state.

        Args:
            data: Dict from to_dict()
            llm_client: Fresh LLMClient instance (not serialized)
            context_summarizer: Optional ContextSummarizerService (not serialized)

        Returns:
            Restored SectionBasedInterview instance ready to continue
        """
        # Create instance with config path and dependencies
        instance = cls(
            llm_client,
            Path(data['config_path']),
            context_summarizer=context_summarizer
        )

        # Restore interview progress state
        instance.current_section_idx = data['current_section_idx']
        instance.completed_sections = data.get('completed_sections', {})
        instance.conversation_history = data.get('conversation_history', [])

        # Restore context and planning data
        instance.context_data = data.get('context_data')
        instance.skeleton_data = data.get('skeleton_data')
        instance.interview_plan = data.get('interview_plan')
        instance.pre_populated_yaml = data.get('pre_populated_yaml')
        instance.questions_needed = data.get('questions_needed', [])
        instance.planning_complete = data.get('planning_complete', False)

        # === VALIDATION: Ensure state is valid for resume ===

        # 1. Bounds check on section index
        if instance.current_section_idx >= len(instance.sections):
            logger.warning(f"Adjusted out-of-bounds section index from {instance.current_section_idx} to {len(instance.sections) - 1}")
            instance.current_section_idx = max(0, len(instance.sections) - 1)

        # 2. If conversation_history is empty but we're mid-interview, re-init section
        if not instance.conversation_history and instance.current_section_idx < len(instance.sections):
            logger.warning("Empty conversation history on restore, re-initializing current section")
            instance._start_section(instance.current_section_idx)

        # NOTE: Resume context message is NOT added here - it would accumulate on every page render.
        # Instead, the caller should add it once when actually restoring from session history
        # by checking st.session_state._session_just_restored flag.

        logger.info(f"Restored interview from dict: section {instance.current_section_idx + 1}/{len(instance.sections)}, "
                   f"{len(instance.completed_sections)} sections completed, "
                   f"{len(instance.conversation_history)} messages in history")

        return instance
