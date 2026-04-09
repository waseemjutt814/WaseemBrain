(* Agent v2 - REAL Production Usage *)
(* This is the REAL agent, not a demo *)

open Agent_real
open Lwt.Syntax

(* Create production agent configuration *)
let production_config = create_config
  ~max_actions:1000
  ~timeout:120.0
  ~thinking:true
  ~working_dir:"."
  ~log_level:Info
  "waseem_agent_v2"
  "Waseem Production Agent"
  "2.0.0"

(* Main agent workflow *)
let run_agent () =
  Printf.printf "\n╔════════════════════════════════════════════════════════════╗\n";
  Printf.printf "║     WASEEM AGENT v2 - REAL PRODUCTION SYSTEM              ║\n";
  Printf.printf "╚════════════════════════════════════════════════════════════╝\n\n";
  
  (* Initialize agent *)
  let agent = create_agent production_config in
  let* () = start_agent agent in
  
  (* Set up context *)
  set_context agent "session_start" (string_of_float (current_timestamp ()));
  set_context agent "user" "waseem";
  set_context agent "project" "WaseemBrain";
  
  Printf.printf "\n[1] Testing File Operations\n";
  Printf.printf "═══════════════════════════════════════\n";
  
  (* REAL Action: Write a file *)
  let test_content = "# Agent v2 Test Output\n\nThis file was created by the REAL OCaml agent.\nTimestamp: " ^ 
    (string_of_float (Unix.gettimeofday ())) ^ "\n" in
  let* write_result = execute_action agent (WriteFile ("agent_output.txt", test_content)) in
  (match write_result with
  | Success msg -> Printf.printf "✓ %s\n" msg
  | Failure msg -> Printf.printf "✗ Write failed: %s\n" msg
  | Partial (_, _) -> Printf.printf "⚠ Partial write\n");
  
  (* REAL Action: Read the file back *)
  let* read_result = execute_action agent (ReadFile "agent_output.txt") in
  (match read_result with
  | Success content -> 
      Printf.printf "✓ File read successfully (%d bytes)\n" (String.length content)
  | Failure msg -> Printf.printf "✗ Read failed: %s\n" msg
  | Partial (_, _) -> Printf.printf "⚠ Partial read\n");
  
  Printf.printf "\n[2] Testing System Commands\n";
  Printf.printf "═══════════════════════════════════════\n";
  
  (* REAL Action: Execute system command *)
  let* cmd_result = execute_action agent (Execute ("echo", ["Agent v2 is running on " ^ Sys.os_type])) in
  (match cmd_result with
  | Success output -> Printf.printf "✓ Command output: %s\n" (String.trim output)
  | Failure msg -> Printf.printf "✗ Command failed: %s\n" msg
  | Partial (out, err) -> Printf.printf "⚠ Partial: %s / %s\n" out err);
  
  (* REAL Action: List directory *)
  let* ls_result = execute_action agent (Execute ("ls", ["-la"])) in
  (match ls_result with
  | Success output -> 
      let lines = String.split_on_char '\n' output in
      Printf.printf "✓ Directory listing (%d items)\n" (List.length lines - 1)
  | Failure msg -> Printf.printf "✗ ls failed: %s\n" msg
  | Partial (_, _) -> Printf.printf "⚠ Partial listing\n");
  
  Printf.printf "\n[3] Testing Git Operations\n";
  Printf.printf "═══════════════════════════════════════\n";
  
  (* REAL Action: Git status *)
  let* git_result = execute_action agent (Git ("status", ["--short"])) in
  (match git_result with
  | Success output -> 
      if String.trim output = "" then
        Printf.printf "✓ Git: Working directory clean\n"
      else
        Printf.printf "✓ Git: Changes detected (%d chars)\n" (String.length output)
  | Failure msg -> Printf.printf "✗ Git failed: %s\n" msg
  | Partial (_, _) -> Printf.printf "⚠ Partial git output\n");
  
  (* REAL Action: Git log *)
  let* git_log = execute_action agent (Git ("log", ["--oneline"; "-5"])) in
  (match git_log with
  | Success output -> 
      let lines = String.split_on_char '\n' (String.trim output) in
      Printf.printf "✓ Recent commits:\n";
      List.iter (fun line -> Printf.printf "   %s\n" line) lines
  | Failure msg -> Printf.printf "✗ Git log failed: %s\n" msg
  | Partial (_, _) -> Printf.printf "⚠ Partial git log\n");
  
  Printf.printf "\n[4] Testing Code Analysis\n";
  Printf.printf "═══════════════════════════════════════\n";
  
  (* REAL Action: Analyze code *)
  let sample_code = "let rec factorial n =\n  if n <= 1 then 1\n  else n * factorial (n - 1)\n\n(* This is a comment *)\nlet result = factorial 5" in
  let* analysis_result = execute_action agent (CodeAnalysis sample_code) in
  (match analysis_result with
  | Success report -> Printf.printf "%s\n" report
  | Failure msg -> Printf.printf "✗ Analysis failed: %s\n" msg
  | Partial (_, _) -> Printf.printf "⚠ Partial analysis\n");
  
  Printf.printf "\n[5] Testing Search\n";
  Printf.printf "═══════════════════════════════════════\n";
  
  (* REAL Action: Search files *)
  let* search_result = execute_action agent (Search ("*.ml", ".")) in
  (match search_result with
  | Success files -> 
      let file_list = String.split_on_char '\n' (String.trim files) in
      Printf.printf "✓ Found %d .ml files:\n" (List.length file_list);
      List.iter (fun f -> if f <> "" then Printf.printf "   - %s\n" f) file_list
  | Failure msg -> Printf.printf "✗ Search failed: %s\n" msg
  | Partial (_, _) -> Printf.printf "⚠ Partial search\n");
  
  (* Process messages *)
  Printf.printf "\n[6] Message Processing\n";
  Printf.printf "═══════════════════════════════════════\n";
  
  let messages = [
    create_message User "Analyze the current project structure";
    create_message User "Check git status and recent commits";
    create_message System "Agent session initialized successfully";
  ] in
  
  let* _ = Lwt_list.iter_s (fun msg ->
    let* result = process_message agent msg in
    match result with
    | Success _ -> Printf.printf "✓ Processed message from %s\n" 
        (match msg.role with User -> "user" | System -> "system" | _ -> "other")
    | _ -> Printf.printf "✗ Failed to process message\n";
    Lwt.return_unit
  ) messages in
  
  (* Show session summary *)
  Printf.printf "\n[7] Session Summary\n";
  Printf.printf "═══════════════════════════════════════\n";
  
  let summary = export_session agent in
  Printf.printf "Agent: %s (v%s)\n" summary.name summary.version;
  Printf.printf "Messages processed: %d\n" summary.message_count;
  Printf.printf "Actions executed: %d\n" summary.action_count;
  Printf.printf "Context items: %d\n" (List.length summary.context);
  Printf.printf "Final state: %s\n" summary.final_state;
  
  (* Show logs *)
  Printf.printf "\n[8] Operation Logs (%d entries)\n";
  Printf.printf "═══════════════════════════════════════\n";
  
  let logs = get_logs agent in
  Printf.printf "Total log entries: %d\n" (List.length logs);
  
  (* Stop agent *)
  let* () = stop_agent agent in
  
  Printf.printf "\n╔════════════════════════════════════════════════════════════╗\n";
  Printf.printf "║              AGENT SESSION COMPLETE                        ║\n";
  Printf.printf "╚════════════════════════════════════════════════════════════╝\n\n";
  
  Lwt.return_unit

(* Entry point *)
let () =
  Random.self_init ();
  try
    Lwt_main.run (run_agent ())
  with
  | exn -> 
      Printf.printf "\n✗ Fatal error: %s\n" (Printexc.to_string exn);
      exit 1
