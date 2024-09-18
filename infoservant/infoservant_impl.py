import json
import logging
import openai
import serpapi
import webpage2content

from typing import Optional, Union, List

LOGGER = logging.getLogger("infoservant")


def _create_system_prompt(has_serpapi: bool = False):
    s = (
        "You're a web browsing bot called infoservant. The user will tell you an instruction or "
        "request that involves accessing the web. You will decide how to use your browsing "
        "capabilities to fulfill the user's needs.\n"
        "\n"
        "You have the following abilities:\n"
        "- Given a URL, you can read the text content of the web page. You can return these "
        "contents to the user if they wish, or you can summarize or discuss them as needed.\n"
    )
    if has_serpapi:
        s += (
            "- You can access Google Search using the SerpApi library, "
            "i.e. serpapi.GoogleSearch(params). With the right params, if you know how to use "
            "the API, you'll be able to find organic search results, access news, and more.\n"
        )
    s += (
        "\n"
        "Because your access to the web is done strictly through a non-interactive text browser, "
        "here are some things you cannot do:\n"
        "- See images\n"
        "- Read PDFs\n"
        "- Fill out forms\n"
        "- Press buttons, move sliders, or operate UI widgets of any kind\n"
        "- See text that gets populated through AJAX\n"
        "- Browse the deep web\n"
        "- Many other things\n"
        "Basically, what you **can** do is read publicly available articles, "
        'official "front page" web content, and other "web 1.0" tasks.'
    )
    return s


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
    conversation.append(
        {
            "role": "assistant",
            "content": answer,
        }
    )

    return answer


def _sanitycheck_user_command(
    conversation: List[dict],
    openai_client: openai.OpenAI,
    apology_out: Optional[List[str]] = None,
) -> bool:
    if type(apology_out) == list:
        # Truncate the list without reassigning it
        apology_out[:] = []
    else:
        apology_out = None

    # Deep-copy so we don't affect the "real" conversation object.
    conversation = json.loads(json.dumps(conversation))
    conversation.append(
        {
            "role": "user",
            "content": (
                "The first thing we need to do is sanity-check the user's request/command. "
                "It might've gotten mangled in transmission, or misparsed, or it could simply "
                "be an inappropriate command issued by a user who doesn't understand what "
                "you do. You need to consider:\n"
                "- Is the command actual readable text?\n"
                "- Can the command be interpreted as a request to access some kind of information "
                "on the web? Maybe it's a URL, maybe it's search terms, maybe it's a question that "
                "requires web access in order to answer?\n"
                "- Does the request require you to do anything outside of your scope? E.g. do they "
                "want you to execute code, solve logic problems, perform extensive calculations, or "
                "otherwise do things that are outside the scope of your directive as a bot that "
                "drives a text-based web browser?\n"
                "\n"
                "Discuss whether or not the user's command constitutes an appropriate request for "
                "you. Provide arguments both pro and con. When you're done, then, on its own line, "
                'write the word "ANSWER: ", just like that, in all caps, followed by either YES '
                "or NO. "
            ),
        }
    )

    discuss_sanitycheck = _call_gpt(
        conversation=conversation,
        openai_client=openai_client,
    )

    if "ANSWER:" not in discuss_sanitycheck:
        if apology_out is not None:
            apology_out.append(
                "I'm sorry, but something went wrong while I was trying to determine the "
                "validity of your request. Please try again."
            )
        return False

    answer = discuss_sanitycheck.split("ANSWER:")[1].upper()
    if "YES" in answer:
        return True

    if apology_out is not None:
        conversation.append(
            {
                "role": "user",
                "content": (
                    "According to a parser's reading of your last message, it appears that you've "
                    "determined that the user's command is inappropriate. Please emit an apology "
                    "to the user explaining why you can't process their request."
                ),
            }
        )

        apology = _call_gpt(
            conversation=conversation,
            openai_client=openai_client,
        )
        apology_out.append(apology)

    return False


def infoservant(
    command: str,
    openai_client: openai.OpenAI,
    serp_api_key: str = "",
):
    if type(command) != str:
        raise ValueError(f"command must be a string (got {type(command)} instead)")
    command = command.strip()
    if not command:
        raise ValueError("Got empty string for command")

    command = command.strip()

    has_serpapi = not not serp_api_key
    conversation = [
        {"role": "system", "content": _create_system_prompt(has_serpapi=has_serpapi)},
        {"role": "user", "content": "The user has issued the following command:"},
        {"role": "user", "content": command},
    ]

    apology_list = []
    is_sane = _sanitycheck_user_command(
        conversation=conversation,
        openai_client=openai_client,
        apology_out=apology_list,
    )
    if not is_sane:
        print(apology_list[0])

    retval = "Hello World"
    return retval


def main():
    import argparse
    import dotenv
    import os

    # Read the version from the VERSION file
    with open(os.path.join(os.path.dirname(__file__), "VERSION"), "r") as version_file:
        version = version_file.read().strip()

    parser = argparse.ArgumentParser(
        description=(
            "An AI that browses text content on the web. Easily integrate intelligent web surfing into any project."
        )
    )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {version}",
        help="Show the version number and exit.",
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

    parser.add_argument(
        "command_arg",
        help="Same as --command, but invoked positionally.",
        type=str,
        nargs="?",
    )

    args = parser.parse_args()

    if args.log_level:
        log_level = logging.getLevelName(args.log_level)
        LOGGER.setLevel(log_level)

    dotenv.load_dotenv()

    openai_api_key = args.key or os.getenv("OPENAI_API_KEY")
    openai_org_id = args.org or os.getenv("OPENAI_ORGANIZATION_ID")
    command = args.command or args.command_arg
    serpapi_key = args.serpapi or os.getenv("SERPAPI_KEY")

    if not command:
        parser.error("Command is required.")
    if not openai_api_key:
        parser.error("OpenAI API key is required.")

    openai_client = openai.OpenAI(api_key=openai_api_key, organization=openai_org_id)

    s = infoservant(
        command=command,
        openai_client=openai_client,
        serp_api_key=serpapi_key,
    )
    print(s)


if __name__ == "__main__":
    main()
