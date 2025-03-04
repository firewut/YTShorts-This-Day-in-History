PROMPT_TEMPLATE = """
Today date is {today}.
You must look for Historical event ( use google ) which happened today years ago and write it as follows:
- It must be about historical events.
- It must be targeted at the general public and safe for kids.
- It must be informative, engaging and entertaining.
- It must avoid controversial topics and violence.
- It must NOT be accompanied by visuals and sound effects.
- It must be around {words_count} words long.
- It must RESPECT Culture and Traditions of those about whom they are spoken.

AVOID these topics:
- colonisation
- conspiracy theory
- death
- gender identity and LGBTQ+ issues
- health and vaccination debates
- historical revisionism
- homophobia
- immigration
- nazism
- patriotism
- political endorsements
- racism
- religion
- sexism
- violence
- war
- weapons
- xenophobia

You should not use the events and words from this list: 
- atomic bomb
- {previous_events}

The script must include only narration, not visuals or sound effects. ONLY NARRATION.
"""

TITLE_TEMPLATE = """
Get title for this text. The title should contain two words that summarize the text. It should be 2 words long.
"""
TAGS_TEMPLATE = """
Get list of tags for text. They should contain 3 tags maximum. Each tag should be one word long. Country names, historical events, and general terms are good tags.
Exclude following words: {exclude_tags}
"""
DESCRIPTION_TEMPLATE = """
Get short summary for text text. It should be around 3 or 4 words long. It should be informative and engaging.
Exclude following words: {exclude_words}
"""

YOUTUBE_VIDEO_TITLE_PREFIX = "Today in history: "
YOUTUBE_VIDEO_DESCRIPTION_SUFFIX = "♥ Generated by AI ♥"
