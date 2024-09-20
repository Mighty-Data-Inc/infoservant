import datetime
import json
import logging
import openai
import serpapi
import time
import webpage2content

from typing import Optional, Union, List

LOGGER = logging.getLogger("infoservant")

JSON_COFFEE_SAMPLE = {
    "urls_to_visit": [
        "http://www.coffee.com",
        "https://wikipedia.com/coffee",
    ],
    "serpapi_calls": [
        {"q": "history of coffee"},
        {"q": "news about coffee", "tbm": "nws"},
        {"q": "buy coffee beans", "tbm": "shop"},
    ],
}


def _chronometer() -> str:
    now = datetime.datetime.utcnow()
    formatted_time = now.strftime("%A, %B %d, %Y, %H:%M:%S.%f")[:-3] + " GMT"
    unix_timestamp_ms = int(time.time() * 1000)
    result = f"CHRONOMETER: Current time is {formatted_time} (Unix millisecond timestamp: {unix_timestamp_ms})"
    return result


def _create_system_prompt(has_serpapi: bool = False):
    s = (
        "You're a web browsing bot called infoservant: an AI that browses text content on "
        "the web. You can conduct deep-dives if needed. You were built for the purpose of "
        "easily integrating intelligent web researching into any project.\n"
        "\n"
        "The user will tell you an instruction or request that involves accessing the web. "
        "You will decide how to use your browsing capabilities to fulfill the user's needs.\n"
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
    convo_intro: List[dict],
    openai_client: openai.OpenAI,
) -> str:
    # Deep-copy so we don't affect the "real" conversation object.
    conversation: List[dict] = json.loads(json.dumps(convo_intro))
    conversation.append(
        {
            "role": "user",
            "content": (
                "The first thing we need to do is sanity-check the user's request/command. "
                "It might've gotten mangled in transmission, or misparsed, or perhaps the "
                "user accidentally pasted binary data into the text field or something. "
                "As such, answer the following question: Is the user's request an intelligible "
                "set of words or symbols that could be reasonably interpreted as either a "
                "natural language request or a web query?\n"
                "\n"
                "Discuss whether or not the user's input is intelligible. Provide arguments "
                "both pro and con. When you're done, then, on its own line, "
                'write the word "ANSWER: ", just like that, in all caps, followed by either YES '
                "or NO. "
            ),
        }
    )

    discuss_intelligible = _call_gpt(
        conversation=conversation,
        openai_client=openai_client,
    )
    discuss_intelligible = discuss_intelligible.upper()

    if "ANSWER:" not in discuss_intelligible:
        raise RuntimeError("Couldn't determine if command is intelligible")

    is_intelligible = "YES" in discuss_intelligible.split("ANSWER:")[1]
    if not is_intelligible:
        raise ValueError("Command isn't intelligible")

    conversation.append(
        {
            "role": "user",
            "content": (
                "Next, let's make sure that the user's command is appropriate "
                "given your operational parameters as a text-browsing bot."
                "- Can the command be interpreted as a request to access some kind of information "
                "on the web? Maybe it's a URL, maybe it's search terms, maybe it's a question that "
                "requires web access in order to answer?\n"
                "- Does the request require you to do anything outside of your scope? E.g. do they "
                "want you to execute code, solve logic problems, perform extensive calculations, or "
                "otherwise do things that are outside the scope of your directive as a bot that "
                "drives a text-based web browser?\n"
                "- Does the user seem to misunderstand what you are and what your purpose is?\n"
                "\n"
                "Discuss whether or not the user's input is appropriate. Provide arguments "
                "both pro and con. When you're done, then, on its own line, "
                'write the word "ANSWER: ", just like that, in all caps, followed by either YES '
                "or NO. "
            ),
        }
    )

    discuss_appropriate = _call_gpt(
        conversation=conversation,
        openai_client=openai_client,
    )
    discuss_appropriate = discuss_appropriate.upper()

    if "ANSWER:" not in discuss_appropriate:
        raise RuntimeError("Couldn't determine if command is appropriate")

    is_appropriate = "YES" in discuss_appropriate.split("ANSWER:")[1]
    if is_appropriate:
        return ""

    conversation.append(
        {
            "role": "user",
            "content": (
                "You've found the user's command to be inappropriate. Instead of rejecting it "
                "outright, let's give the user the benefit of the doubt and assume that they're "
                "just looking for information or conducting research. Think of ways to reframe, "
                "rephrase, or reinterpret the user's request in a way that would make it "
                "more appropriate for you. For example, if the user was asking you to perform "
                "a complex task, then maybe what they really want is to look up instructions to "
                "perform that task themselves?\n"
                "\n"
                "Brainstorm some ways to rephrase the user's request into something you can "
                "handle. Once you've evaluated this matter, on its own line, emit the word "
                '"REPHRASE:", just like that, in all caps, with the colon. After "REPHRASE:", '
                'write the rephrased query, or "N/A" if you\'ve determined '
                "that the user's inquiry can't be rephrased into something you can act on.\n"
                "\n"
                "Remember that you are rephrasing *for yourself*, not for the user. The user "
                "will never see this rephrase. This rephrase is simply part of your own "
                "chain-of-thought process.\n"
                "\n"
                "Don't say anything else after your rephrase. I'll be passing your output "
                'through a parser, splitting on the string "REPHRASE:", so it\'s important '
                "that, once you emit the rephrase, you then stay quiet."
            ),
        }
    )

    discuss_rephrase = _call_gpt(
        conversation=conversation,
        openai_client=openai_client,
    )
    if "REPHRASE:" not in discuss_rephrase:
        raise RuntimeError("Couldn't rephrase command into something appropriate")

    rephrase = discuss_rephrase.split("REPHRASE:", maxsplit=1)[1].strip()
    return rephrase


def _estimate_reasonable_time(
    convo_intro: List[dict],
    openai_client: openai.OpenAI,
    seconds_permitted: int = 0,
) -> str:
    # Deep-copy so we don't affect the "real" conversation object.
    conversation: List[dict] = json.loads(json.dumps(convo_intro))
    conversation.append(
        {
            "role": "user",
            "content": (
                "Think about the complexity and intricacy of the user's command or request, and "
                "how much detail and inference they'll want in their response. Based on these "
                "factors, how quickly do you think the user can reasonably expect an answer? "
                "On the one hand, if the user is expecting nothing more than the full text of "
                "some web page as-is, then there's no reason to keep them waiting for more than "
                "a few seconds at most. On the other hand, if they want extensive research on a "
                "complex topic, then it's not unreasonable for them to accept that you might "
                "need at least several minutes to browse a large number of sources and "
                "investigate the topic in depth.\n"
                "\n"
                "Discuss the complexity of the user's request and formulate a reasonable "
                "ballpark expectation for the duration that it might take you to execute this "
                'command. When you\'re done, then, on its own line, emit the word "ANSWER:", '
                "just like that, in all caps followed by a colon. Then, after the colon, "
                "on the same line, write the time duration that you've come up with."
            ),
        }
    )

    discuss_timedur = _call_gpt(
        conversation=conversation,
        openai_client=openai_client,
    )

    if "ANSWER:" not in discuss_timedur:
        raise RuntimeError("Couldn't determine a reasonable duration estimate")

    timedur_est = discuss_timedur.split("ANSWER:")[1].strip()

    if "\n" in timedur_est:
        # The LLM emitted some nonsense after the answer.
        timedur_est = timedur_est.split("\n", 1)[0]

    return timedur_est


def _run_one_research_task(
    task: dict,
    openai_client: openai.OpenAI,
):
    task_type = task.get("task_type")

    if task_type == "url":
        url = task.get("url")
        if not url:
            task["success"] = False
            task["error"] = "URL not provided"
            return False
        try:
            result = webpage2content.webpage2content(
                url=url,
                openai_client=openai_client,
            )
        except Exception as ex:
            task["success"] = False
            task["error"] = f"Exception while fetching url {url}: {ex}"
            return False
        if not result:
            task["success"] = False
            task["error"] = f"Fetch of {url} produced empty/invalid result"
            return False
        task["success"] = True
        task["result"] = result
        return True

    if task_type == "serpapi_call":
        serpapi_params = task.get("params")
        if not serpapi_params:
            task["success"] = False
            task["error"] = "SerpApi params not provided"
            return False
        try:
            search = serpapi.GoogleSearch(serpapi_params)
            result = search.get_dict()
        except Exception as ex:
            task["success"] = False
            task["error"] = f"Exception while performing SerpApi query: {ex}"
            return False
        CLEANUP_FIELDS = [
            "pagination",
            "serpapi_pagination",
            "filters",
            "search_metadata",
            "search_parameters_xxxxxx",
            "search_information",
            "knowledge_graph",
            "inline_videos",
        ]
        for field in CLEANUP_FIELDS:
            if field in result:
                del result[field]
        task["success"] = True
        task["result"] = json.dumps(result, indent=2)
        return True

    return False


def _task_results_to_conversation_messages(tasks: List[dict]):
    messages = []

    for task in tasks:
        task_type = task.get("task_type")

        task_success = task.get("success") == True
        task_result = task.get("result")
        task_error = task.get("error")

        message = ""
        if task_type == "url":
            url = task.get("url")
            message = f"You browsed URL: {url}\n"
        elif task_type == "serpapi_call":
            serpapi_params = task.get("params")
            message = (
                f"You called SerpApi with these parameters:\n"
                f"{json.dumps(serpapi_params, indent=2)}\n"
            )
        if not task_success:
            message += f"The call failed with the following error:\n{task_error}"
        else:
            message += "The call succeeded with the following results:\n\n---\n\n"
            message += task_result

        messages.append({"role": "system", "content": message})

    return messages


def _summarize_progress_so_far(
    conversation: List[dict],
    openai_client: openai.OpenAI,
):
    conversation.append({"role": "system", "content": ("Write a ")})


def _research_cycle(
    convo_intro: List[dict],
    time_start: float,
    pages_explored: List[dict],
    searches_conducted: List[dict],
    openai_client: openai.OpenAI,
    serp_api_key: str = "",
):
    # Deep-copy so we don't affect the "real" conversation object.
    conversation: List[dict] = json.loads(json.dumps(convo_intro))

    time_now = time.time()
    time_spent = time_now - time_start
    conversation.append(
        {
            "role": "system",
            "content": (
                f"{_chronometer()}\n"
                "\n"
                f"You've been working for {time_spent} seconds so far."
            ),
        }
    )

    s = ""
    if serp_api_key:
        s = "What search queries will you conduct?"
    conversation.append(
        {
            "role": "system",
            "content": (
                "From here, list your next actions as a text-browsing web bot. "
                f"What URLs will you visit? {s}\n"
                "\n"
                "Don't write any code or JSON yet. Write your output in plain English. "
                "For now, we're just brainstorming."
            ),
        }
    )

    _call_gpt(
        conversation=conversation,
        openai_client=openai_client,
    )

    json_sample = json.loads(json.dumps(JSON_COFFEE_SAMPLE))
    if not serp_api_key:
        del json_sample["serpapi_calls"]
    instructions_str = (
        "Okay, now emit a JSON structure to express these next steps.\n"
        "\n"
        'The JSON structure will have a field called "urls_to_visit", containing a list of '
        "strings representing URLs to visit. Don't order more than 5 such URLS at a time.\n"
        "\n"
    )
    if serp_api_key:
        instructions_str += (
            'The JSON structure will also have a field called "serpapi_calls", which will have '
            "a list of objects that contain the parameters of SerpApi calls "
            "(using engine=google). Don't worry about the `api_key` field of the SerpApi calls; "
            "the parsing engine will populate it for you as it reads your JSON output. You just "
            "focus on the URLs to visit and the parameters of the SerpApi calls to make. Don't "
            "issue more than 3 SerpApi calls at a time.\n"
            "\n"
        )
    instructions_str += (
        "Imagine the user asks for information about coffee. Then "
        "the JSON might look something like this:\n\n"
        "```json\n"
        f"{json.dumps(json_sample, indent=2)}\n"
        "```\n"
    )

    conversation.append({"role": "system", "content": instructions_str})

    completion = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=conversation,
        temperature=0,
        response_format={"type": "json_object"},
    )
    str_nextstep_json = completion.choices[0].message.content
    nextsteps: List[dict] = json.loads(str_nextstep_json)

    tasks = []
    if "urls_to_visit" in nextsteps and type(nextsteps["urls_to_visit"]) == list:
        for item in nextsteps["urls_to_visit"]:
            tasks.append({"task_type": "url", "url": item})

    if (
        serp_api_key
        and ("serpapi_calls" in nextsteps)
        and type(nextsteps["serpapi_calls"]) == list
    ):
        for item in nextsteps["serpapi_calls"]:
            item.update(
                {
                    "api_key": serp_api_key,
                    "num": 5,
                    "no_cache": True,
                    "output": "json",
                }
            )
            task = {
                "task_type": "serpapi_call",
                "params": item,
            }
            tasks.append(task)

    # TODO: Run these concurrently.
    for task in tasks:
        _run_one_research_task(
            task=task,
            openai_client=openai_client,
        )

    result_msgs = _task_results_to_conversation_messages(tasks)
    conversation.extend(result_msgs)

    conversation.append(
        {
            "role": "system",
            "content": (
                "Write a comprehensive report about what you've done so far, what you've learned "
                "from your web browsing, and how it relates to the user's initial command or "
                "inquiry. Note the searches you've conducted (if any), the pages you've visited "
                "(if any), the information you've gathered, and which pages specific important "
                "pieces of information or significant quotes or block-quotes came from. This "
                'report should essentially present a complete "state dump", such that, if '
                "someone else were to try to continue this research from where you've left off, "
                "they'll have everything they need to reestablish your current informational "
                "context."
            ),
        }
    )
    _call_gpt(
        conversation=conversation,
        openai_client=openai_client,
    )
    print(conversation[-1]["content"])

    print(json.dumps(result_msgs, indent=2))
    exit(0)

    pass


def infoservant(
    command: str,
    openai_client: openai.OpenAI,
    serp_api_key: str = "",
    seconds_permitted: int = 0,
):
    if type(command) != str:
        raise ValueError(f"command must be a string (got {type(command)} instead)")
    command = command.strip()
    if not command:
        raise ValueError("Got empty string for command")

    time_start = time.time()

    command = command.strip()

    has_serpapi = not not serp_api_key
    convo_intro = [
        {"role": "system", "content": _create_system_prompt(has_serpapi=has_serpapi)},
        {"role": "system", "content": "The user has issued the following command:"},
        {"role": "user", "content": command},
    ]

    command_rephrase = _sanitycheck_user_command(
        convo_intro=convo_intro,
        openai_client=openai_client,
    )
    if command_rephrase:
        command = command_rephrase
        convo_intro[2]["content"] = command_rephrase

    if seconds_permitted:
        convo_intro.append(
            {
                "role": "system",
                "content": (
                    f"The user believes that you should be able to complete this task "
                    f"in approximately {seconds_permitted} seconds. This time window, "
                    "depending on how short or long it is, provides you with some "
                    "information about how concise or detailed, respectively, the "
                    "user would like your answer to be."
                ),
            }
        )

    # We add a brief exchange to establish what kind of output we're looking for.
    convo_intro.append(
        {
            "role": "system",
            "content": (
                "Make some inferences about the user's expectations of you. "
                "What kind of response is the user expecting? "
                "What structure or format of reply would make the user satisfied "
                "with the answer? What's too little, and what's too much?"
            ),
        }
    )
    _call_gpt(
        conversation=convo_intro,
        openai_client=openai_client,
    )

    timedur_est = _estimate_reasonable_time(
        convo_intro=convo_intro,
        openai_client=openai_client,
    )
    convo_intro.append(
        {
            "role": "assistant",
            "content": (
                "Given the scope of the user's request, here is what I believe to "
                "be a reasonable time allotment for spending on this problem: "
                f"{timedur_est}"
            ),
        }
    )

    _research_cycle(
        convo_intro=convo_intro,
        time_start=time_start,
        pages_explored=[],
        searches_conducted=[],
        openai_client=openai_client,
        serp_api_key=serp_api_key,
    )

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
            "The instructions to resolve via web browsing. These are typically a short "
            "plain-English statement of information to find, a question to answer, or "
            "even just the URL of a web page to retrieve."
        ),
        type=str,
    )

    parser.add_argument(
        "-t",
        "--time",
        help=(
            "How much time to grant the bot for executing this command, in seconds. "
            "Once this time duration has been exceeded, the bot compiles whatever "
            "information it's collected so far, and writes a final report. This means that the "
            "bot will likely exceed this exact execution time by a margin proportional to "
            "the time taken to write a final report, usually a few seconds to a minute."
        ),
        type=int,
        default=0,
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
        seconds_permitted=args.time,
    )
    print(s)


if __name__ == "__main__":
    main()
