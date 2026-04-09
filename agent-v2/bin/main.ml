(* Agent v2 - Main Entry Point *)
(* Demonstrates the agent framework capabilities *)

open Agent
open Lwt.Syntax

let demo_config = {
  id = "agent_v2_demo";
  name = "Waseem Agent v2";
  version = "2.0.0";
  max_actions = 10;
  timeout_seconds = 30.0;
  enable_thinking = true;
}

let run_demo () =
  Printf.printf "\n=== Waseem Agent v2 Demo ===\n\n";
  
  (* Create agent *)
  let agent = create_agent demo_config in
  
  (* Start agent *)
  let* () = start_agent agent in
  
  (* Create and process messages *)
  let messages = [
    create_message User "Hello, can you help me with a task?";
    create_message User "Search for files containing 'test' in the codebase";
    create_message User "Execute: ls -la";
  ] in
  
  (* Process messages sequentially *)
  let* results = Lwt_list.map_s (fun msg ->
    let* result = process_message agent msg in
    match result with
    | Success content ->
        Printf.printf "✓ %s\n" content;
        Lwt.return (Ok content)
    | Failure msg ->
        Printf.printf "✗ Failed: %s\n" msg;
        Lwt.return (Error msg)
    | Partial (out, err) ->
        Printf.printf "⚠ Partial: %s (Error: %s)\n" out err;
        Lwt.return (Ok out)
  ) messages in
  
  (* Demonstrate actions *)
  Printf.printf "\n=== Action Execution Demo ===\n\n";
  
  let actions = [
    Think "Planning to analyze the current directory structure";
    Execute ("echo", ["Hello from Agent v2"]);
    Search ("*.ml", "current directory");
  ] in
  
  let* action_result = chain_actions actions in
  (match action_result with
  | Success result -> Printf.printf "\nAction chain result:\n%s\n" result
  | Failure msg -> Printf.printf "\nAction chain failed: %s\n" msg
  | Partial (out, err) -> Printf.printf "\nPartial: %s\nError: %s\n" out err);
  
  (* Show context usage *)
  Printf.printf "\n=== Context Management Demo ===\n\n";
  set_context agent "session_start" (string_of_float (current_timestamp ()));
  set_context agent "user_name" "Waseem";
  
  (match get_context agent "user_name" with
  | Some name -> Printf.printf "User: %s\n" name
  | None -> Printf.printf "User not set\n");
  
  (* Show message history *)
  Printf.printf "\n=== Message History (%d messages) ===\n\n" (List.length (get_messages agent));
  get_messages agent |> List.iter (fun msg ->
    let role_str = match msg.role with
      | User -> "User"
      | Assistant -> "Assistant"
      | System -> "System"
      | Tool -> "Tool"
    in
    Printf.printf "[%s] %s: %s\n" 
      (Unix.localtime msg.timestamp |> fun t -> 
        Printf.sprintf "%02d:%02d:%02d" t.Unix.tm_hour t.Unix.tm_min t.Unix.tm_sec)
      role_str
      (if String.length msg.content > 50 
       then String.sub msg.content 0 50 ^ "..."
       else msg.content)
  );
  
  (* Stop agent *)
  let* () = stop_agent agent in
  
  Printf.printf "\n=== Demo Complete ===\n";
  Lwt.return_unit

let () =
  Random.self_init ();
  Lwt_main.run (run_demo ())
