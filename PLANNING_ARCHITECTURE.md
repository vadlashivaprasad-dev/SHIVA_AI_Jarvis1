# PLANNING ARCHITECTURE - COGNITIVE OS

## Current State
- Hardcoded templates returning same 5 steps
- No goal decomposition
- No constraint handling
- No multi-step reasoning

## Target: HTN (Hierarchical Task Network) Planner

### HTN Planning vs. Current

**Current:**
\\\
Goal: "Help user with task"
→ Always returns: [perceive, analyze, plan, execute, reflect]
(same 5 steps regardless of goal)
\\\

**HTN:**
\\\
Goal: "Debug Python code"
→ Plan:
  1. [Ask user for error message]
  2. [Search similar errors in knowledge base]
  3. [IF found: suggest fix ELSE: analyze code]
  4. [Explain solution]
  5. [Track for learning]
(Adaptive, conditional, multi-step)
\\\

---

## HTN Task Hierarchy

\\\
Primitive Tasks (directly executable)
  - query_knowledge
  - search_web
  - call_api
  - generate_text
  - execute_code

Compound Tasks (decompose into subtasks)
  - solve_problem = analyze ∘ generate_solutions ∘ evaluate
  - debug = identify_issue ∘ find_root_cause ∘ suggest_fix
  - research = search ∘ summarize ∘ synthesize
  - plan_project = decompose_goals ∘ estimate ∘ schedule

Abstract Tasks (flexible execution)
  - clarify_user_intent = ask_followups | infer_from_context
  - find_solution = search_knowledge | generate_new | delegate
\\\

---

## HTN Planning Algorithm

\\\python
class HTNPlanner:
    def plan(self, goal, state):
        """Decompose abstract goal to executable steps."""
        
        # 1. Select decomposition method based on goal type
        if goal.type == "debugging":
            methods = self.debug_methods
        elif goal.type == "research":
            methods = self.research_methods
        else:
            methods = self.generic_methods
        
        # 2. Try each method until success
        for method in methods:
            # 3. Decompose compound task
            subtasks = method.decompose(goal)
            
            # 4. Check preconditions
            if all(s.precondition(state) for s in subtasks):
                
                # 5. Order with dependency constraints
                ordered = self.topological_sort(subtasks)
                
                # 6. Add parallelizable tasks
                with_parallelism = self.add_parallelism(ordered)
                
                return with_parallelism
        
        # Fallback to generic plan
        return self.default_plan(goal)
    
    def decompose_goal(self, goal):
        """HTN decomposition."""
        if goal.type == "coding_task":
            return [
                Task("understand_requirements"),
                Task("check_existing_code"),
                Task("implement_solution"),
                Task("test_solution"),
                Task("document_code")
            ]
    
    def respect_constraints(self, plan):
        """Ensure all constraints satisfied."""
        # Time constraints: goal must complete < deadline
        # Resource constraints: can't use more tokens than available
        # Ordering constraints: B cannot start until A finishes
        # Logical constraints: certain actions must be in sequence
        pass
\\\

---

## Constraint Satisfaction

\\\
Constraints:

Time: Plan.duration < goal.deadline
Cost: Plan.tokens < budget
Ordering: Task B cannot start before Task A
Precedence: Task C requires Task A and B complete first
Mutual Exclusion: Cannot call both APIs simultaneously
Logic: IF goal is "risky" THEN require approval step
\\\

---

## Replanning on Failure

\\\python
def execute_plan_with_replanning(plan, goal):
    for step in plan:
        result = execute(step)
        
        if result.failed:
            # Replan from this point
            remaining_goal = goal.subtract_completed(step)
            new_plan = planner.plan(remaining_goal)
            plan = combine_executed(step) + new_plan
            
            # Continue with new plan
            return execute_plan_with_replanning(new_plan, goal)
    
    return result.success
\\\

---

## Performance Targets

| Operation | Target |
|---|---|
| Goal decomposition | < 500ms |
| Constraint checking | < 100ms |
| Replan on failure | < 1s |
| 5-step plan execution | < 5s total |

