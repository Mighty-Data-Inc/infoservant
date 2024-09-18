import logging
import openai
import serpapi
import webpage2content

from bs4 import BeautifulSoup

from typing import Optional, Union, List

LOGGER = logging.getLogger("infoservant")


def _call_gpt(
    conversation: Union[str, dict, List[dict]],
    openai_client: openai.OpenAI,
) -> str:
    if isinstance(conversation, str):
        conversation = [{"role": "user", "content": conversation}]
    elif isinstance(conversation, dict):
        conversation = [conversation]

    LOGGER.debug(
        f"infoservant._call_gpt calling chat completion "
        f"with conversation of {len(conversation)} messages. "
        f"Last message is {len(conversation[-1]['content'])} chars long."
    )

    completion = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=conversation,
        temperature=0,
    )

    answer = completion.choices[0].message.content

    LOGGER.debug(f"infoservant._call_gpt got answer of length {len(answer)}")

    if completion.choices[0].finish_reason == "length":
        LOGGER.debug(f"infoservant._call_gpt answer truncated")
        answer += (
            "\n\n...(There is more material to cover, but this response is already "
            "excessively lengthy. As such, I have to stop here for now.)"
        )

    answer = answer.strip()
    return answer


def infoservant(
    command: str,
    openai_client: openai.OpenAI,
    serp_api_key: str = "",
):
    print("Hello World")


def main():
    import argparse
    import dotenv
    import os

    parser = argparse.ArgumentParser(
        description=(
            "An AI that browses text content on the web. Easily integrate intelligent web surfing into any project."
        )
    )
    parser.add_argument(
        "-l",
        "--log-level",
        help="Sets the logging level. (default: %(default)s)",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    )
    parser.add_argument(
        "-k",
        "--key",
        help="OpenAI API key. If not specified, reads from the environment variable OPENAI_API_KEY.",
        type=str,
    )
    parser.add_argument(
        "-o",
        "--org",
        help="OpenAI organization ID. If not specified, reads from the environment variable OPENAI_ORGANIZATION. "
        "If no such variable exists, then organization is not used when calling the OpenAI API.",
        type=str,
    )
    parser.add_argument(
        "-s",
        "--serpapi",
        help="SerpApi key. If not provided, will run without SerpApi capabilities.",
        type=str,
    )
    parser.add_argument(
        "-c",
        "--command",
        help=(
            "The instructions to resolve via web browsing. These are typically a short plain-English "
            "statement of information to find, a question to answer, or even just the URL of a "
            "web page to retrieve."
        ),
        type=str,
    )

    args = parser.parse_args()

    if args.log_level:
        log_level = logging.getLevelName(log_level)
        LOGGER.setLevel(log_level)

    dotenv.load_dotenv()

    openai_api_key = (args.key or os.getenv("OPENAI_API_KEY") or "",)
    openai_org_id = args.org or os.getenv("OPENAI_ORGANIZATION_ID") or None
    openai_client = openai.OpenAI(api_key=openai_api_key, organization=openai_org_id)

    serpapi_key = args.serpapi or os.getenv("SERPAPI_KEY") or ""

    s = infoservant(
        command=args.command,
        openai_client=openai_client,
        serp_api_key=serpapi_key,
    )
    print(s)


if __name__ == "__main__":
    main()
