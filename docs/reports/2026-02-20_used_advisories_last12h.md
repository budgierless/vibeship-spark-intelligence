# Used Advisories (helpful_counted=true, rolling last 12h)

- Window start (epoch): 1771495952.812
- Window end (epoch): 1771539152.812
- Helpful advisories in window: **52**

## How “used” is measured
- Source: `~/.spark/advisor/effectiveness.json -> recent_outcomes`
- Rule: `helpful_counted == true` within last 12h.
- This is the same underlying signal used by KPI `good_advice_used` (rolling window).

## List
1. `prefetch_team_coordination_edit`
   - text: Use Edit conservatively with fast validation and explicit rollback safety.
   - tool=Edit | route=packet_relaxed | trace=9ee1152bcf613992 | pos_outcomes=1
2. `c685c0c93f1b`
   - text: [Caution] Glob failed 4/17 times (76% success rate). Most common: Ripgrep search timed out after 20 seconds. The search may have matched files but
   - tool=Glob | route=live | trace=8ac0571bc5e0e325 | pos_outcomes=0
3. `cognitive:user_understanding:can_we_actually_bring_a_certain_set_of_v`
   - text: Can we actually bring a certain set of very, very important, really key guardrails that AGIs would have, so that, whatever mode we are running, even though it is the automated mode, it would have certain guardrails? These would actually kee
   - tool=Read | route=live | trace=1b2ffe2fd21b117c | pos_outcomes=0
4. `cognitive:user_understanding:you_can_also_give_me_a_mid-journey_promp`
   - text: You can also give me a mid-journey prompt too, so that I can actually bring you something that is easier from these, if you want, and then we can actually try to transform that, if you want me to, or if these are going to be good for you, t
   - tool=TaskOutput | route=live | trace=37b0d05f0e8dfff4 | pos_outcomes=0
5. `cognitive:user_understanding:with_the_way_that_we_have_written_the_sp`
   - text: With the way that we have written the SPARK AI manifesto, I think it is not looking like a readable book. It has so many of these things, and at the bottom it is trying to make you click on things and other stuff like that, which breaks act
   - tool=Glob | route=live | trace=765d739d2d94e006 | pos_outcomes=0
6. `cognitive:user_understanding:can_we_right_now_try_to_build_the_projec`
   - text: Can we right now try to build the project from end to end and see whether all of these new systems are working? So that we can actually try to one-shot projects to a really good status. What would you want to test one-shotting right now? Cr
   - tool=Write | route=live | trace=aae914676756e2cb | pos_outcomes=1
7. `cognitive:trigger:destructive_commands:0ac66335`
   - text: Run a dry-run or backup before irreversible operations.
   - tool=Bash | route=live | trace=2b289c44aab5df7d | pos_outcomes=2
8. `cognitive:context:can_we_now_build_the_project_end_to_end_`
   - text: Can we now build the project end to end and test whether this new system that we brought in for full execution from end to end is working as it should After pushing github
   - tool=Read | route=live | trace=0599a3637c2022c3 | pos_outcomes=0
9. `eidos:eidos:heuristic:8acf7acb`
   - text: (text not present in feedback log for this id)
   - tool=- | route=- | trace=-
10. `eidos:eidos:heuristic:67940817`
   - text: [EIDOS HEURISTIC] When similar to 'make it so that kimi is spawni', start with approach like 'Execute: wc -l "C:/Users/USER/AppData/Local/Temp/'
   - tool=Bash | route=live | trace=350e6ac4fef197c6 | pos_outcomes=0
11. `cognitive:user_understanding:user_prefers:_the_spark_here:_c:\users\u`
   - text: User prefers: the spark here: c:\Users\USER\Desktop\vibeship-spark-pulse
   - tool=Read | route=live | trace=912ad545c6372af3 | pos_outcomes=0
12. `prefetch_performance_latency_read`
   - text: Use Read conservatively with fast validation and explicit rollback safety.
   - tool=Write | route=packet_relaxed | trace=98e7653d735dfd4e | pos_outcomes=0
13. `prefetch_testing_validation_edit`
   - text: For Edit, prioritize reproducible checks and preserve failing-case evidence.
   - tool=Task | route=packet_relaxed | trace=711af4996e665318 | pos_outcomes=0
14. `prefetch_emergent_other_edit`
   - text: Use Edit conservatively with fast validation and explicit rollback safety.
   - tool=Edit | route=packet_exact | trace=0c22107f179adeeb | pos_outcomes=1
15. `prefetch_emergent_other_bash`
   - text: Use Bash conservatively with fast validation and explicit rollback safety.
   - tool=Bash | route=packet_relaxed | trace=2002bd990e341536 | pos_outcomes=0
16. `cognitive:user_understanding:when_using_bash,_remember:_do_that_after`
   - text: When using Bash, remember: Do that after pushing this git up.
   - tool=TaskCreate | route=live | trace=7d68807ee7ebab8c | pos_outcomes=0
17. `live-n1`
   - text: (text not present in feedback log for this id)
   - tool=- | route=- | trace=-
18. `cognitive:wisdom:principle:Show dont tell - demonstrate with real e`
   - text: Show dont tell - demonstrate with real examples
   - tool=WebFetch | route=live | trace=b8ac11adfc51e001 | pos_outcomes=0
19. `cognitive:context:test:_pipeline_verification_successful`
   - text: Test: Pipeline verification successful
   - tool=WebSearch | route=live | trace=d59eec142d47de83 | pos_outcomes=0
20. `cognitive:trigger:deployment:64546d17`
   - text: Before deploy: run tests, verify migrations, and confirm env vars.
   - tool=Edit | route=live | trace=f308e7b61ce2ad47 | pos_outcomes=0
21. `prefetch_testing_validation_bash`
   - text: For Bash, prioritize reproducible checks and preserve failing-case evidence.
   - tool=Bash | route=packet_exact | trace=8b32b075fd0af44e | pos_outcomes=0
22. `prefetch_tool_reliability_read`
   - text: Keep Read steps minimal and validate assumptions before irreversible changes.
   - tool=Read | route=packet_relaxed | trace=cec44fcc6a3a7e75 | pos_outcomes=0
23. `prefetch_research_decision_support_bash`
   - text: Use Bash conservatively with fast validation and explicit rollback safety.
   - tool=Bash | route=packet_relaxed | trace=f94ebac836de540d | pos_outcomes=0
24. `prefetch_tool_reliability_edit`
   - text: Keep Edit steps minimal and validate assumptions before irreversible changes.
   - tool=Edit | route=packet_relaxed | trace=8dea03712fd6d4a2 | pos_outcomes=0
25. `prefetch_research_decision_support_edit`
   - text: Use Edit conservatively with fast validation and explicit rollback safety.
   - tool=Edit | route=packet_relaxed | trace=d5c1c98f7a9b323a | pos_outcomes=0
26. `baseline_emergent_other`
   - text: Use conservative, test-backed edits and verify assumptions before irreversible actions. Next check: `python -m pytest -q`.
   - tool=Grep | route=packet_relaxed | trace=7b7b87b0aa47878b | pos_outcomes=0
27. `cognitive:trigger:auth_security:7174e383`
   - text: Validate authentication inputs server-side and avoid trusting client checks.
   - tool=OpenClawLLM | route=live | trace=7215a3d107a0d8ac0a66 | pos_outcomes=0
28. `cognitive:context:constraint:_in_**exactly_one_state**_at_`
   - text: Constraint: in **exactly one state** at all times
   - tool=Task | route=live | trace=d47616251375f980 | pos_outcomes=0
29. `prefetch_tool_reliability_bash`
   - text: Keep Bash steps minimal and validate assumptions before irreversible changes.
   - tool=Bash | route=packet_relaxed | trace=042e6a8325cbca23 | pos_outcomes=0
30. `prefetch_performance_latency_edit`
   - text: Use Edit conservatively with fast validation and explicit rollback safety.
   - tool=Glob | route=packet_relaxed | trace=95e8d9fa08668b98 | pos_outcomes=0
31. `prefetch_emergent_other_read`
   - text: Use Read conservatively with fast validation and explicit rollback safety.
   - tool=TaskUpdate | route=packet_relaxed | trace=fa1e324d2b333b56 | pos_outcomes=0
32. `prefetch_auth_security_edit`
   - text: Before Edit, validate auth assumptions and avoid exposing secrets in logs.
   - tool=Edit | route=packet_relaxed | trace=3439ff4b0660bfd3 | pos_outcomes=2
33. `prefetch_auth_security_read`
   - text: Before Read, validate auth assumptions and avoid exposing secrets in logs.
   - tool=Read | route=packet_relaxed | trace=808c00e0d4d0fdac | pos_outcomes=0
34. `prefetch_auth_security_bash`
   - text: Before Bash, validate auth assumptions and avoid exposing secrets in logs.
   - tool=Task | route=packet_relaxed | trace=8a36fc24fd3b6316 | pos_outcomes=0
35. `cognitive:trigger:auth_security:25da832f`
   - text: Never log secrets or tokens; redact sensitive data in logs.
   - tool=OpenClawLLM | route=live | trace=db2fd05a2d49e5c8b09c | pos_outcomes=0
36. `prefetch_orchestration_execution_bash`
   - text: Use Bash on critical-path tasks first; unblock dependencies before parallel work.
   - tool=Bash | route=packet_exact | trace=de4cecba911e20b4 | pos_outcomes=1
37. `cognitive:reasoning:is_it_possible_to_now_build_something_wh`
   - text: is it possible to now build something where this podcast can have the avatar of Spark reading talking with lip sync within a video, so that we can improve podcast to a video format we can use in clips and videos too, what would be the best
   - tool=WebSearch | route=live | trace=1b5c5d84ac7f12be | pos_outcomes=0
38. `eidos:eidos:heuristic:6a0abe4d`
   - text: [EIDOS HEURISTIC] When Edit .env (replace 'ELEVENLABS_API_KEY=sk_47eff81456e1fa7996'), try: Modify .env: 'ELEVENLABS_API_KEY=sk_fd6cbb1ab32a627393'
   - tool=Edit | route=live | trace=25591d8eac198346 | pos_outcomes=0
39. `prefetch_testing_validation_read`
   - text: For Read, prioritize reproducible checks and preserve failing-case evidence.
   - tool=TaskUpdate | route=packet_relaxed | trace=3ac026d979a28074 | pos_outcomes=0
40. `baseline_schema_contracts`
   - text: Check schema or contract compatibility before editing interfaces or payload shapes. Next check: `python -m pytest -q`.
   - tool=Bash | route=packet_relaxed | trace=5bc0cccfae8cdcf3 | pos_outcomes=0
41. `prefetch_schema_contracts_read`
   - text: Before Read, verify schema and contract compatibility to avoid breaking interfaces.
   - tool=Read | route=packet_relaxed | trace=3189afac2ca9f1d1 | pos_outcomes=0
42. `eidos:eidos:heuristic:d5cf82a0`
   - text: [EIDOS HEURISTIC] When Read mcp.ts, try: Inspect mcp.ts
   - tool=Edit | route=live | trace=6fa49ea157f5d3c6 | pos_outcomes=0
43. `cognitive:user_understanding:i_like_most_of_it,_but_there_are_so_many`
   - text: I like most of it, but there are so many of these, the background lines and the blobs of colours and stuff like that, that is kind of looking weird as well as some patterns in the background that are filling so much space with I don't know
   - tool=Bash | route=live | trace=56ec2c154ede2d47 | pos_outcomes=0
44. `cognitive:reasoning:i_see_that_there_is_a_certain,_how_can_i`
   - text: I see that there is a certain, how can I say it's all about the nodes in the background, and they don't feel too alive. Can we change the background a little bit, please? Instead of making it only about notes, which is kind of old-school, l
   - tool=Read | route=live | trace=19c5a15db169f2cf | pos_outcomes=0
45. `cognitive:reasoning:anything_is_missing_before_we_push_this_`
   - text: Anything is missing before we push this to life. Can you check please? Deep analysis. Also, just double check with all the Spark systems that we have too so that it reflects them perfectly. If there are still gaps, let's actually fill those
   - tool=Task | route=live | trace=674bf04d8c9ff77f | pos_outcomes=0
46. `prefetch_deployment_ops_read`
   - text: Use reversible steps for Read and verify rollback conditions first.
   - tool=Write | route=packet_relaxed | trace=900a76868c275264 | pos_outcomes=0
47. `cognitive:trigger:destructive_commands:b5b07cde`
   - text: Double-check destructive commands and confirm targets before executing.
   - tool=Bash | route=live | trace=181a339dcdb7d635 | pos_outcomes=0
48. `cognitive:reasoning:perfect_thank_you,_now_can_we_do_it_so_t`
   - text: perfect thank you, now can we do it so that Spark can directly connect to Codex, Claude, Minimax, Kimi terminals, and spawn workers needed from here as an option, instead of just being something that works with OpenClaw. We have a Codex ORr
   - tool=Read | route=live | trace=190db6e2fc68d07c | pos_outcomes=0
49. `cognitive:reasoning:yes_let's_build_the_right_structures_on_`
   - text: yes let's build the right structures on these with these elements and other gaps to be filled too so that they work perfectly in the canvas as well
   - tool=Write | route=packet_relaxed | trace=9511e819ab0d93e0 | pos_outcomes=0
50. `eidos:eidos:heuristic:d2a3e76b`
   - text: [EIDOS HEURISTIC] When Edit gauntlet.py (replace 'print(f"        After P@5={a'), try: Modify gauntlet.py: '_log(f"        After P@5={af'
   - tool=Edit | route=live | trace=3f58f9f37359e031 | pos_outcomes=0
51. `cognitive:context:constraint:_observable**_(every_step_cha`
   - text: Constraint: observable** (every step changes something)
   - tool=Write | route=live | trace=47fd75fa1e277617 | pos_outcomes=0
52. `9df84cbcdbd5`
   - text: [Caution] WebFetch fails repeatedly with: Request failed with status code 404
   - tool=WebFetch | route=live | trace=68ff7cae76f0d573 | pos_outcomes=0