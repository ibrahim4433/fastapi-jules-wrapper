1\. Can we send a picture or file with the prompt using this tool API?

Not directly in the current repoless setup. The Jules API POST /v1alpha/sessions endpoint primarily accepts a text prompt. In a standard Jules session, files are provided by giving him a sourceContext (a link to a GitHub repository). Because we are forcing a "repoless" session to make him act like a stateless LLM, he doesn't have a repo to read files from. Note: If Jules eventually supports multi-modal image inputs in the prompt string (like Gemini does with base64 images), the proxy could be updated to parse OpenAI's image\_url message format and pass it along.



2\. Can we grab/download/pull a file or folder from Jules if he made one?

Yes, but it depends on the session type.



In our Repoless Proxy: We explicitly blocked him from making files. He is only allowed to output text.

In a Stateful/Repo Session: If you give Jules a GitHub repo, he creates files by generating ChangeSets (Git patches). The Jules API documentation (which we saw in the activities logs) shows that whenever Jules makes a file, it creates an Artifact activity containing a ChangeSet or GitPatch. You can easily pull that patch from the API and apply it locally. He can also generate Media artifacts (like images) or BashOutput logs which you can extract directly from the activities API!

3\. Can we edit his environment/system configs or know his system details?

You cannot configure the VM specs, but you CAN explore it! Google does not expose API endpoints to change the RAM, CPU, or OS of the Jules VM—it is a standardized, isolated container managed by Google. However, because Jules has the ability to run bash commands, you can prompt him to explore his own system! You could send a prompt like: "Run uname -a and cat /etc/os-release and output the results." He will execute those commands on his internal Linux VM and return the system details back to you.



4\. Can we send another message to the same Jules session and grab the result?

Absolutely! The Jules API documentation explicitly lists a POST /v1alpha/{session=sessions/\*}:sendMessage endpoint. Our FastAPI wrapper currently creates a brand new session for every request because we are mimicking the stateless OpenAI /v1/chat/completions endpoint. However, if you wanted to mimic the OpenAI Assistants API (which remembers conversation history), you could easily modify our proxy to:



Save the session\_id to a database.

When the user sends a follow-up message, instead of calling POST /sessions, the proxy calls POST /v1alpha/sessions/{session\_id}:sendMessage.

The proxy then goes right back into the GET /activities polling loop to wait for his next agentMessaged response!

