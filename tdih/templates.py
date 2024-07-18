PROMPT_TEMPLATE = """
Today date is {today}. 

You must get "today in history" and write it as follows:
- It must be about historical events.
- It must be around {read_length} seconds read.
- It must be targeted at the general public and safe for kids.
- It must be informative, engaging and entertaining.
- It must avoid controversial topics and violence.
- It must NOT be accompanied by visuals and sound effects.
- It must be around 30 words long.

AVOID following topics:
{previous_events} 
- nazism
- racism
- sexism
- homophobia
- xenophobia
- violence
- war

The script must include only narration, not visuals or sound effects. ONLY NARRATION.
"""
