Phase 1 — Foundation & Environment Setup
1
Python Environment + Virtual Environment
💡 Why: Every Python project needs an isolated environment so libraries don't conflict with other projects on your laptop.
Installed Python 3.11
Created virtual environment with python -m venv venv
Created requirements.txt with all dependencies
2
AWS Account + Bedrock Model Access
💡 Why: Your AI needs a brain (LLM). Amazon Nova Pro is the model that reads questions and writes answers. Without enabling it, nothing works.
Enabled Amazon Nova Pro v1 in Bedrock console
Enabled Amazon Titan Embed Text v2 (for converting text to vectors)
Configured AWS credentials with aws configure
3
IAM Role — DevOpsAIAssistantRole
💡 Why: AWS security requires explicit permission to use each service. This role tells AWS "this bot is allowed to use Bedrock, DynamoDB, OpenSearch, S3."
Created IAM role with Bedrock invoke permissions
Added DynamoDB read/write permissions
Added OpenSearch Serverless API access
Added S3 read permissions for runbooks
Added CloudWatch logs permissions
📚 Phase 2 — Knowledge Base (Where the Bot Learns From)
4
OpenSearch Serverless — Vector Database
💡 Why: The bot needs a special database that stores text as numbers (vectors) so it can find similar content by meaning, not just keywords. This is the brain's long-term memory.
Created OpenSearch Serverless collection: devops-runbooks
Configured k-NN index with HNSW algorithm, cosine similarity
Set embedding dimension to 1024 (matching Titan Embed output)
Added IAM role + personal user ARN to data access policy
5
Confluence Loader — Company Wiki
💡 Why: Your team's runbooks and procedures are stored in Confluence. The bot needs to read them so it can answer "How do we roll back?" from your actual company docs.
Created Confluence free account + DEVOPS space
Created runbook pages (Kubernetes rollback, error codes, Lambda deploy)
Built ingestion/loaders/confluence_loader.py using Atlassian API
Generated API token from id.atlassian.com
6
Jira Loader — Ticket History
💡 Why: Past incidents are tracked in Jira. When an engineer asks about error DB-502, the bot can find similar past Jira tickets and how they were resolved.
Built ingestion/loaders/jira_loader.py
Configured project key, JQL query for relevant tickets
Reused same Atlassian API token (no extra setup needed)
7
GitHub Loader — Code Repository Docs
💡 Why: README files, architecture docs, and deployment configs live in GitHub. The bot indexes these so it can answer questions about your actual codebase.
Built ingestion/loaders/github_loader.py
Fixed personal account vs org issue — used gh.get_user() not gh.get_organization()
Indexed repos: infra, platform, services
8
S3 Loader — PDF Runbooks
💡 Why: Some runbooks exist as PDF files in S3 (not in Confluence). The bot needs to read these too so no knowledge is left out.
Built ingestion/loaders/s3_loader.py
Configured S3 bucket: devops-runbooks-s3-bucket
Uploaded company profile PDFs for testing
9
Chunking + Embeddings + Ingestion Pipeline
💡 Why: Long documents must be cut into small pieces (chunks) before being converted to vectors. A 10-page runbook becomes 50 searchable chunks — each chunk can be found independently.
Built ingestion/chunker.py — 800 char chunks, 150 overlap
Built embeddings/bedrock_embeddings.py — Titan Embed v2, 1024 dimensions
Built ingestion/pipeline.py — orchestrates all 4 loaders
Successfully ran pipeline — all docs indexed in OpenSearch
🔍 Phase 3 — Search & Retrieval (Finding the Right Answers)
10
Vector Search (KNN) — Semantic Search
💡 Why: Normal search finds exact words. Vector search finds meaning. "Pod crashing" finds docs about "container failing" even though the words are different.
Built vectorstore/opensearch_client.py — KNN similarity search
Built vectorstore/index_manager.py — index creation and management
Verified search returning relevant chunks with similarity scores
11
BM25 Keyword Search — Exact Match Search
💡 Why: Vector search is great for meaning but misses exact matches like "kubectl rollout undo" or "DB-502". BM25 finds exact words. Having both gives the best of both worlds.
Added bm25_search() method to opensearch_client.py
Used OpenSearch match query for keyword scoring
12
Hybrid Search — Combined Vector + BM25
💡 Why: Running both searches and merging results gives much better accuracy than either alone. 32 combined results are deduplicated to the best 11 unique docs.
Built rag/retriever.py — HybridRetriever class
Runs both KNN + BM25, merges 32 results, deduplicates by URL
Verified: 16 vector + 16 BM25 = 32 merged → 11 unique chunks
13
LLM Re-ranking — Nova Scores Each Chunk
💡 Why: OpenSearch scores by statistical similarity, not true relevance. Re-ranking asks Nova "which of these 10 chunks actually answers the question?" — much more accurate.
Built rag/reranker.py — BedrockReranker using Nova
Nova scores each chunk 0.0-1.0 for relevance to the question
Verified: IAC-5512 correctly scored 0.95, Amazon PDF correctly scored 0.05
14
RAG Chain — Retrieval + Nova Answer Generation
💡 Why: RAG (Retrieval Augmented Generation) combines search + AI. Instead of Nova guessing, it reads your actual company docs and answers from them — no hallucination.
Built rag/chain.py — retrieves chunks then calls Nova
Fixed Nova message format issue (messages array required)
Tested: correct answers returned with source URLs cited
🤖 Phase 4 — AI Agent (The Decision-Making Brain)
15
Agent State + LangGraph Graph
💡 Why: A simple RAG chain just searches and answers. An agent THINKS — it decides whether to use tools, loops until it has enough info, and tracks everything in a state object.
Built agent/state.py — AgentState TypedDict with all fields
Built agent/graph.py — StateGraph with 6 nodes and conditional edges
Added loop control: max 3 iterations before forcing answer
Added singleton pattern — graph built once, reused for all messages
16
Agent Nodes — 6 Processing Steps
💡 Why: Breaking the agent into separate nodes makes each step clear, testable, and debuggable. If something goes wrong, you know exactly which node failed.
load_memory_node — loads past conversations from DynamoDB
retrieve_context_node — runs hybrid search in OpenSearch
reason_and_plan_node — Nova decides if tools are needed
execute_tools_node — runs CloudWatch/Jira/GitHub tools
synthesise_answer_node — Nova writes final answer
save_memory_node — saves Q&A to DynamoDB
17
MCP Tools — CloudWatch, GitHub, Jira, Slack
💡 Why: Tools let the agent get LIVE data. Instead of just reading docs, it can query real CloudWatch logs, check actual GitHub PRs, and search real Jira tickets.
Built mcp/aws_mcp.py — CloudWatch logs query
Built mcp/github_mcp.py — GitHub PR info fetcher
Built mcp/slack_mcp.py — Slack message sender
Built agent/tools.py — 4 tools with @tool decorator and error handling
Verified: Nova automatically calls tools when needed (e.g. search_jira for IAC-5512)
💾 Phase 5 — Memory (The Bot Remembers You)
18
DynamoDB Tables — Conversation + Incident Memory
💡 Why: Without memory, the bot forgets every conversation. DynamoDB stores past Q&A so the bot remembers "last week Sagar asked about Lambda deploy" and gives connected answers.
Created devops-ai-memory table — session_id (PK) + timestamp (SK) + 7-day TTL
Created devops-ai-incidents table — error_code (PK) + timestamp (SK)
Built memory/dynamodb_memory.py — get_history, save_turn, save_incident, get_incident
Verified: history grows from 9 → 10 after each conversation
💬 Phase 6 — Slack Bot (The User Interface)
19
Slack App + Socket Mode Connection
💡 Why: Engineers live in Slack. Instead of a web app nobody uses, the bot lives where engineers already work — they just @mention it and get answers without leaving Slack.
Created Slack App at api.slack.com
Configured Socket Mode (no ngrok, no Lambda, no public URL needed)
Got SLACK_BOT_TOKEN (xoxb-) + SLACK_APP_TOKEN (xapp-)
Set permissions: app_mentions:read, chat:write, channels:history
Enabled app_mention event subscription
20
Slack Bot Handler — handler.py
💡 Why: This is the glue that connects Slack to your AI agent. When you @mention the bot, this file receives the message, cleans it, runs the agent, and posts the answer back.
Built slack_bot/handler.py with handle_mention() function
Added clean_question() to strip <@mention> tags from questions
Added "Thinking... ⏳" immediate response so user knows bot is working
Added Slack Block Kit formatting with clickable source links
Added 7-step structured logging with file + function names
Added flush=True to all prints so logs appear instantly
🧪 Phase 7 — Testing & Verification
21
End-to-End Testing — test_agent.py + test_slack.py
💡 Why: Testing each component individually confirmed each piece works. Then end-to-end testing confirmed everything works together as one system.
Tested AWS MCP client — CloudWatch log query
Tested GitHub MCP client — PR info fetch
Tested HybridRetriever — 7 chunks returned with scores
Tested RAG chain — correct answers with source URLs
Tested each LangGraph node individually
Tested full agent with test_agent.py — all nodes executed correctly
Tested in real Slack — IAC-5512 question answered correctly with Jira tool use
22
Output Quality Verification + Bug Fixes
💡 Why: Real-world testing revealed small issues. Fixing them made the system reliable and the terminal logs easy to understand for debugging.
Fixed Nova message format (ValidationException — messages array required)
Fixed GitHub loader for personal accounts (get_user vs get_organization)
Suppressed noisy library warnings (DeprecationWarning, INFO logs)
Removed print statements from retriever.py and dynamodb_memory.py
Added sys.stdout.reconfigure for immediate terminal output
Verified reranker correctly scores IAC-5512 at 0.95, noise PDFs at 0.05
🎉 What You Built — In Simple Terms
You built an AI system that: reads your company docs → stores them as smart vectors → when an engineer asks a question in Slack, it searches docs using two methods → re-ranks results with AI → decides if it needs live data from CloudWatch/Jira/GitHub → generates an accurate cited answer → remembers the conversation for next time. This is what companies spend months and millions building.
