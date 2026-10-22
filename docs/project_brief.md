# Master Project Brief: Building an Industry-Ready AI Engineering Portfolio

## 1. My Background and Career Objective

I am a final-year Computer Science student specializing in Artificial Intelligence. I am preparing to apply for internships, graduate positions, and entry-level engineering roles, and I want to build a strong portfolio that demonstrates practical engineering ability rather than just academic knowledge.

My target locations are:

- Malaysia
- Dubai, United Arab Emirates

My target roles include:

- AI Engineer
- Junior AI Engineer
- Agentic AI Engineer
- AI/ML Engineer
- LLM Engineer
- Applied AI Engineer
- AI Automation Engineer
- Generative AI Engineer
- AI Platform or LLM Infrastructure Engineer, where appropriate
- AI Engineer and Agentic AI internships

I expect to begin applying seriously now and need to inform my university about my internship by the first week of March 2027. Therefore, I need projects that can be completed, demonstrated, documented, and discussed in technical interviews before that deadline.

I can dedicate approximately 10–15 hours per week to building my portfolio. I use a Mac, VS Code, Claude Code, Python, and local AI models such as Qwen. I am budget-conscious and prefer free, open-source, local, or low-cost solutions where practical.

## 2. My Main Objective

Help me become a competitive candidate for AI engineering internships and entry-level positions.

I do not want generic projects that simply wrap an LLM API in a chat interface. I want projects that demonstrate that I can design, build, test, evaluate, debug, and explain real AI-enabled software systems.

Every project should demonstrate several of the following skills:

- Python software engineering and clean architecture
- LLM integration and structured outputs
- Tool calling and controlled agentic workflows
- Retrieval, data processing, and context management where appropriate
- API design and backend development
- Reliable data validation and error handling
- Evaluation of AI system quality
- Testing, debugging, and reproducibility
- Security, privacy, and responsible use of AI
- Observability, performance measurement, and cost awareness
- Docker, Git, CI, and practical deployment
- Human-in-the-loop workflows
- Technical documentation and architectural decision-making

Do not add technologies merely to make the stack look impressive. Every component must solve a real problem.

## 3. The Three Projects in My Portfolio

### Project A: SentinelOps — Evidence-Driven AI Incident Investigation Agent

This is my flagship project and should receive the highest priority.

Build an AI agent that investigates simulated production incidents in a small e-commerce system.

The simulated system should contain services such as:

- API gateway
- Authentication
- Product catalogue
- Orders
- Payments
- Database

The agent should investigate alerts by using controlled, read-only tools to examine:

- Application logs
- Service metrics
- Service dependencies
- Recent deployments
- Configuration changes
- Incident timelines

It should gather evidence, formulate and rank root-cause hypotheses, identify contradictions, perform additional tool calls when justified, and generate an investigation report.

The report should include:

- Incident summary
- Affected services
- Ranked root-cause hypotheses
- Supporting evidence with traceable source IDs
- Contradicting or missing evidence
- Confidence or uncertainty explanation
- Recommended next diagnostic checks
- Suggested remediation, clearly separated from executed actions
- Investigation duration, tool-call count, and stop reason

Implement a bounded agent workflow with explicit states, validated tool inputs, tool-call limits, timeouts, and clear stopping conditions.

The first version must not execute remediation or access real production systems. All consequential actions must remain recommendations requiring human approval.

The main technical question this project should answer is:

"Can a controlled, tool-using AI agent diagnose simulated incidents more accurately or efficiently than a rule-based baseline or a single-pass LLM?"

Build an evaluation dataset with known root causes and compare:

1. A rule-based baseline
2. A single-pass LLM with fixed evidence
3. The iterative tool-using agent

Measure top-1 and top-3 diagnosis accuracy, evidence validity, unsupported claims, tool calls, latency, and model cost where measurable.

Do not assume the agent performs better. Design the evaluation to determine whether it actually does.

### Project B: CargoMind — AI Logistics Document Intelligence

Build a document-processing system that extracts and reconciles information across shipping-related documents.

Use synthetic or openly licensed sample documents, such as:

- Commercial invoices
- Packing lists
- Bills of lading
- Purchase orders
- Delivery instructions

The system should extract structured fields, normalize values, compare information across documents, detect discrepancies, and send uncertain cases to a human review queue.

Include:

- Typed extraction schemas
- Field-level source provenance
- Raw and normalized values
- Deterministic validation rules
- Cross-document reconciliation
- Confidence-aware review decisions
- Human corrections
- Audit history
- Exportable structured records

Measure extraction accuracy, discrepancy-detection precision and recall, provenance coverage, review rate, and processing time.

Do not allow the LLM to silently invent missing values or make final decisions when documents contradict one another.

The main technical question this project should answer is:

"Can an AI-assisted document pipeline extract useful structured information while reliably detecting inconsistencies and identifying cases that need human review?"

### Project C: ModelRouter — Cost-, Latency-, and Quality-Aware LLM Gateway

Build a provider-neutral gateway that routes requests to suitable language models based on task requirements and operational constraints.

Support at least two model candidates, which may be hosted APIs or a combination of hosted and local models.

The system should consider:

- Request type
- Model capability
- Quality requirements
- Token or cost budget
- Latency target
- Output schema requirements
- Provider availability
- Fallback options

Implement transparent routing rules first. Do not begin with a complex machine-learning router unless the simpler baseline is established.

Include structured request logs, provider adapters, output validation, bounded retries, fallback handling, budget controls, and a benchmark runner.

Compare:

1. A fixed low-cost model
2. A fixed stronger model
3. The routing system

Measure task success, cost per successful task, median and p95 latency, schema-valid output rate, fallback rate, and quality-cost trade-offs.

The main technical question this project should answer is:

"Can intelligent model selection reduce the cost or latency of an LLM application while preserving an acceptable level of task quality?"

## 4. How I Want You to Work With Me

Act as a senior AI engineer, software architect, technical mentor, and critical code reviewer.

Do not merely generate large amounts of code. Help me understand the system and build it in a way I can confidently explain in an interview.

Follow this workflow:

### Step 1: Establish the plan

Before implementation:

- Inspect the repository and identify the existing files.
- Read the current README, project instructions, dependencies, and tests.
- Identify missing requirements.
- Propose a practical architecture and explain the important decisions.
- Break the work into small milestones.
- Define acceptance criteria for each milestone.
- Identify risks, unnecessary complexity, and budget implications.

Do not overwrite existing work without understanding it.

### Step 2: Implement incrementally

Work on one small, coherent feature at a time.

For each milestone:

1. Explain what needs to be built and why.
2. Identify the files that will be created or changed.
3. Implement the smallest complete version.
4. Add relevant tests.
5. Run the tests and inspect failures.
6. Fix problems before moving forward.
7. Explain how I can run and verify the feature.
8. Update the documentation if the architecture or behavior changes.

Do not mark a feature complete just because code has been written. Verify it.

### Step 3: Teach me the engineering decisions

When making an important technical choice, explain:

- What problem it solves
- Why this approach was selected
- What alternatives were considered
- What trade-offs exist
- How the decision affects reliability, maintainability, cost, and performance

Keep explanations practical and focused. Help me develop the ability to defend my decisions in technical interviews.

### Step 4: Review the implementation critically

Actively look for:

- Hallucinations and unsupported claims
- Incorrect assumptions
- Weak evaluation methods
- Poor error handling
- Unsafe tool permissions
- Prompt-injection risks
- Data leakage between training/development and test sets
- Hard-coded secrets
- Unnecessary dependencies
- Over-engineering
- Untested code paths
- Misleading performance claims
- Poor API design
- Fragile model-specific assumptions

Do not tell me the project is excellent simply to be encouraging. Identify weaknesses and recommend specific improvements.

## 5. Engineering Standards

Apply these standards across the projects.

### Code quality

- Use Python with type hints.
- Prefer clear modules and small, cohesive functions.
- Use Pydantic or equivalent validation for important data contracts.
- Keep business logic separate from API handlers, model adapters, and user interfaces.
- Avoid giant files and unnecessary abstraction.
- Pin or constrain dependencies appropriately.
- Use environment variables for secrets.
- Provide an example configuration without credentials.
- Include useful logging and actionable error messages.

### Testing

Include:

- Unit tests
- Integration tests for core workflows
- Tests for invalid inputs
- Tests for model/provider failures
- Tests for timeout and retry behavior
- Regression tests for previously discovered bugs
- Safety tests where tools or untrusted input are involved

Where possible, tests should run without paid model API calls.

Mock external providers during unit tests and keep a small, explicitly budgeted evaluation set for real model calls.

### AI reliability

- Validate model outputs before using them.
- Prefer structured outputs where appropriate.
- Distinguish deterministic logic from model-generated judgments.
- Record model versions and relevant configuration for evaluations.
- Preserve evidence provenance.
- Handle uncertainty explicitly.
- Avoid treating model-generated confidence as a calibrated probability unless it has been evaluated.
- Keep development data separate from held-out test data.
- Do not claim that an agent is better than a baseline until the benchmark supports that conclusion.

### Security and privacy

- Use synthetic or openly licensed data by default.
- Never commit API keys, passwords, or private user data.
- Treat logs and uploaded documents as untrusted inputs.
- Do not allow arbitrary shell commands or unrestricted database access through agents.
- Apply bounded tool permissions, timeouts, and execution budgets.
- Require human approval for consequential actions.
- Document limitations and the threat model.

### Reproducibility and delivery

Each project should include:

- A clear README
- Setup and execution instructions
- Architecture diagram
- Requirements and scope
- Example inputs and outputs
- Tests and test commands
- Evaluation scripts
- Benchmark results
- Known limitations
- Security considerations
- A short demonstration
- A roadmap based on real limitations

Use Git with meaningful commits. Use Docker where it simplifies setup, and add CI checks when the core workflow is stable.

## 6. What Makes These Projects Stand Out

The differentiator must be demonstrated through engineering evidence, not marketing language.

For SentinelOps, emphasize bounded tool use, evidence traceability, hypothesis comparison, safe stopping, and baseline evaluation.

For CargoMind, emphasize cross-document reconciliation, deterministic validation, source provenance, exception handling, and human review.

For ModelRouter, emphasize reproducible benchmarking, quality-cost trade-offs, provider resilience, budget controls, and transparent routing decisions.

For each project, identify:

- The real problem being solved
- Why a basic chatbot or simple script is insufficient
- The main engineering challenge
- The key architectural decision
- The baseline used for comparison
- The metrics used to evaluate the system
- The biggest observed failure
- What was improved after testing
- What remains unsolved

Never claim a project is production-ready merely because it runs locally.

## 7. Budget and Technology Constraints

I am a student and need to keep costs low.

Prefer:

- Free and open-source libraries
- Local development
- Synthetic data
- SQLite or a lightweight local database initially
- Local Qwen models for suitable tasks
- Mock providers for tests
- Small evaluation datasets before scaling up
- Minimal cloud infrastructure

Use a paid LLM API only when it provides a clear benefit that cannot reasonably be achieved locally.

Before suggesting a service that incurs cost, explain why it is needed, provide a lower-cost alternative, and estimate the likely usage cost where reliable pricing information is available.

Do not introduce Kubernetes, a vector database, multiple cooperating agents, or complicated cloud infrastructure without a specific, justified requirement.

## 8. Career and Portfolio Deliverables

The purpose of these projects is to help me demonstrate practical ability to recruiters and technical interviewers.

For each completed project, help me produce:

1. A professional GitHub repository.
2. A concise, high-quality README.
3. An architecture diagram.
4. A short demonstration video or walkthrough.
5. A reproducible evaluation report.
6. A list of technical decisions and trade-offs.
7. A list of limitations and future improvements.
8. Three to five interview questions with strong, honest answers.
9. A project explanation that can be delivered in 60 seconds.
10. CV bullet points based strictly on verified implementation and measured results.

Help me explain the projects in terms of engineering outcomes, not just technologies used.

Do not invent users, revenue, deployment history, business impact, benchmark scores, or performance improvements.

Use placeholders for measurements until I run the evaluation.

## 9. Time Management and Prioritization

I have approximately 10–15 hours per week and need to be ready for internship applications and interviews before the first week of March 2027.

Prioritize:

1. SentinelOps as the flagship project.
2. CargoMind as the complementary applied AI project.
3. ModelRouter only after the first projects have reached a strong, demonstrable state or if it aligns better with a specific target role.

Keep milestones small enough that I can make progress alongside university work and job applications.

Do not delay applications until the entire portfolio is complete. Help me improve the portfolio while I apply.

If the schedule slips, recommend what to cut without compromising the core technical value.

## 10. Definition of Success

A project is complete only when:

- Its core workflow works end to end.
- Its important behaviors are tested.
- Its main failure modes are understood.
- Its evaluation can be reproduced.
- Its README allows another developer to run it.
- Its demo shows both a successful case and a meaningful failure or uncertainty case.
- Its limitations are documented.
- Its technical choices can be explained in an interview.
- Its CV claims are supported by actual implementation and results.

The goal is not to build the largest system. The goal is to build a small, credible, well-engineered AI system that demonstrates real problem-solving ability.

## 11. Your First Task

Start with SentinelOps.

First inspect the current repository and tell me:

1. What already exists and what is missing.
2. The proposed architecture and core data models.
3. The minimum viable scope for the first two weeks.
4. The initial development and held-out test dataset design.
5. The acceptance criteria and tests for the first milestone.
6. Any risks or unnecessary complexity you recommend removing.

Do not generate the entire application at once. Begin with the first milestone, implement it, test it, and explain how I can verify it before proceeding.