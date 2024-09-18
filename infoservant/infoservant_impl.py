import logging
import openai
import serpapi
import webpage2content

from bs4 import BeautifulSoup

from typing import Optional, Union, List
from contextlib import contextmanager


def _call_gpt(
    conversation: Union[str, dict, List[dict]],
    openai_client: openai.OpenAI,
    logger: Optional[logging.Logger] = None,
) -> str:
    if isinstance(conversation, str):
        conversation = [{"role": "user", "content": conversation}]
    elif isinstance(conversation, dict):
        conversation = [conversation]

    answer_full = ""
    while True:
        if logger:
            logger.debug(
                f"webpage2content._call_gpt calling chat completion "
                f"with conversation of {len(conversation)} messages. "
                f"Last message is {len(conversation[-1]['content'])} chars long."
            )

        completion = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=conversation,
            temperature=0,
        )

        answer = completion.choices[0].message.content
        answer_full += answer + "\n"

        if logger:
            logger.debug(
                f"webpage2content._call_gpt got answer of length {len(answer)}, "
                f"appending to full answer currently at length {len(answer_full)}"
            )

        conversation.append(
            {
                "role": "assistant",
                "content": answer,
            }
        )
        conversation.append(
            {
                "role": "user",
                "content": "Please continue from where you left off.",
            }
        )

        if completion.choices[0].finish_reason == "length":
            if logger:
                logger.debug(
                    "webpage2content._call_gpt finish reason length, continuing loop"
                )
            continue

        break

    answer_full = answer_full.strip()
    return answer_full


def webpage2content(
    url: str,
    openai_client: openai.OpenAI,
    logger: Optional[logging.Logger] = None,
):
    if not logger:
        logger = logging.getLogger(__name__)

    markdown = _get_page_as_markdown(url, logger=logger)
    if not markdown:
        return None

    if not isinstance(markdown, str):
        logger.error("markdown somehow came back as something other than a string.")
        return None

    markdown = markdown.strip()
    if not markdown:
        return None

    mdlines = markdown.splitlines()
    mdlines = [f"{linenum+1}. {linetext}" for linenum, linetext in enumerate(mdlines)]
    markdown_with_linenums = "\n".join(mdlines)

    # TODO: Break up the markdown into pieces if the webpage is too big.
    conversation = [
        {"role": "system", "content": SYSTEMPROMPT},
        {"role": "user", "content": markdown_with_linenums},
    ]

    # First, we get the AI to describe the page to us in its own words.
    # We are uninterested in this answer. We just want it to have this conversation
    # with itself so that it knows what's going to be important in subsequent steps.
    try:
        logger.debug(f"webpage2content is asking GPT to describe {url}")
        gptreply_page_description = _call_gpt(
            conversation=conversation,
            openai_client=openai_client,
            logger=logger,
        )
        logger.debug(f"webpage2content asked GPT to describe {url}")
        conversation.append({"role": "assistant", "content": gptreply_page_description})
    except Exception:
        logger.exception("Exception in webpage2content determining content type")
        return None

    # Next, we simply ask it whether or not the content is human-readable.
    try:
        logger.debug(f"webpage2content is determining human readability of {url}")
        conversation.append({"role": "user", "content": PROMPT_HUMAN_READABLE_CHECK})
        gptreply_is_human_readable = _call_gpt(
            conversation=conversation,
            openai_client=openai_client,
            logger=logger,
        )

        is_human_readable = "yes" in gptreply_is_human_readable.lower()
        if not is_human_readable:
            logger.warning(f"Page at URL {url} is not human-readable")
            return None
        else:
            logger.debug(f"webpage2content confirmed human readability of {url}")

    except Exception:
        logger.exception("Exception in webpage2content checking human readability")
        return None

    # At last, we call it with the line filtration prompt.
    try:
        logger.debug(f"webpage2content is querying line filtration for {url}")
        conversation[-1] = {"role": "user", "content": PROMPT_LINE_FILTER}
        gptreply_line_filtration = _call_gpt(
            conversation=conversation,
            openai_client=openai_client,
            logger=logger,
        )
        logger.debug(f"webpage2content has queried line filtration for {url}")

    except Exception:
        logger.exception("Exception in webpage2content choosing lines to filter")
        return None

    mdlines = markdown.splitlines()
    filterlines = gptreply_line_filtration.splitlines()

    logger.debug(f"webpage2content is iterating through line filtration for {url}")

    for filterline in filterlines:
        try:
            linenumstr, linetext = filterline.split(".", maxsplit=1)
            linenum = int(linenumstr) - 1

            if linetext.lower().endswith("discard"):
                mdlines[linenum] = ""

        except Exception as ex:
            logger.debug(f"Nonthreatening exception during line filtration: {ex}")
            pass

    markdown = "\n".join(mdlines)
    markdown = re.sub(r"\n\n\n+", "\n\n", markdown)
    markdown = markdown.strip()

    logger.debug(f"webpage2content has constructed filtered markdown for {url}")
    return markdown


def main():
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Usage: webpage2content <URL> [OPENAI_API_KEY]")
        sys.exit(1)

    url = sys.argv[1]

    OPENAI_API_KEY = None
    if len(sys.argv) > 2:
        OPENAI_API_KEY = sys.argv[2]

    openai_client = None
    if OPENAI_API_KEY:
        openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
    else:
        openai_client = openai.OpenAI()

    try:
        content = webpage2content(url, openai_client=openai_client)
        print(content)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
