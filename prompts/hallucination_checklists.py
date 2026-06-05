# Category-specific hallucination checklists for the adversarial hallucination detector

CHECKLISTS = {

    "Job Role and Career Trends": """
- SALARY GROUNDING: Flag salary numbers, compensation figures, or package ranges not grounded in verified sources.
- YEAR ALIGNMENT: Ensure market trends, hiring trends, and salary references match the source year.
- PLACEMENT CLAIMS: Flag deterministic claims like "this role guarantees placement" or "easy to get jobs."
- MARKET TRENDS: Verify claims about demand, layoffs, hiring growth, and role popularity.
""",

    "Resume Writing": """
- ATS CLAIMS: Flag unsupported statistics regarding ATS systems, recruiter behavior, resume scanning times, etc.
- QUANTITATIVE CLAIMS: Verify percentages and numeric resume claims are sourced or hedged.
- RESUME BEST PRACTICES: Ensure recommendations are not stated as absolute rules unless verified.
""",

    "Placement Roadmaps": """
- TIME ESTIMATES: Verify roadmap durations are internally consistent and realistic.
- TOOL VALIDATION: Verify technologies, platforms, courses, and frameworks actually exist.
- DEPENDENCY CHECK: Ensure prerequisites logically precede advanced topics.
- OUTCOME CLAIMS: Flag guaranteed placement or unrealistic promises.
""",

    "Interview Question Collections": """
- QUESTION CORRECTNESS: Verify technical questions are factually correct.
- SOLUTION VALIDATION: Ensure provided answers actually solve the questions.
- ROUND STRUCTURE CLAIMS: Verify company-specific interview structures are sourced.
""",

    "DSA and Coding": """
- CODE MANUAL TRACE: Manually validate logic, syntax, and variable flow.
- TIME COMPLEXITY: Verify Big-O claims match implementations.
- SPACE COMPLEXITY: Verify auxiliary space calculations.
- DATA STRUCTURE BEHAVIOR: Verify stack, queue, heap, tree, graph operations.
- OUTPUT MATCHING: Ensure examples match actual code execution.
""",

    "Comparison Articles": """
- BALANCE: Ensure comparisons are fair and not biased.
- FEATURE VALIDATION: Verify claims about tools, frameworks, and technologies.
- TRADEOFF CHECK: Ensure advantages/disadvantages are realistic and grounded.
""",

    "AI Technology": """
- MODEL CLAIMS: Verify claims regarding model capabilities, limitations, context lengths, and benchmarks.
- TECHNICAL ATTRIBUTION: Verify technologies are attributed correctly.
- ARCHITECTURE CLAIMS: Validate AI architecture descriptions and terminology.
- PERFORMANCE CLAIMS: Flag unsupported accuracy, benchmark, or capability claims.
""",

    "Developer Technology": """
- TECH ATTRIBUTION: Verify technologies belong to correct companies/projects.
- FRAMEWORK VALIDATION: Verify APIs, libraries, tools, and frameworks exist and are correctly named.
- VERSION SENSITIVITY: Verify version-specific claims if mentioned.
- CODE CORRECTNESS: Ensure implementation details are technically valid.
""",

    "generic": """
- TECH ATTRIBUTION: Verify technologies are correctly named and attributed.
- CODE CORRECTNESS: Ensure code syntax and logic are technically valid.
- QUANTITATIVE CLAIMS: Ensure salary, statistics, or metrics are grounded in sources or properly hedged.
"""
}
