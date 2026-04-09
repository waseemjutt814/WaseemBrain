(* Agent v2 - High-level OCaml Agent Framework *)
(* Core agent types and functionality *)

open Lwt.Syntax

(* Agent Types *)
type agent_id = string
type session_id = string

type message_role = User | Assistant | System | Tool

type message = {
  id : string;
  role : message_role;
  content : string;
  timestamp : float;
  metadata : (string * string) list;
}

type action =
  | Execute of string * string list  (* command, args *)
  | ReadFile of string
  | WriteFile of string * string
  | HttpRequest of string * string * (string * string) list  (* method, url, headers *)
  | Search of string * string  (* pattern, scope *)
  | Think of string  (* reasoning step *)

type action_result =
  | Success of string
  | Failure of string
  | Partial of string * string  (* output, error *)

type agent_state =
  | Idle
  | Processing of string
  | Executing of action
  | Error of string

type agent_config = {
  id : agent_id;
  name : string;
  version : string;
  max_actions : int;
  timeout_seconds : float;
  enable_thinking : bool;
}

type agent = {
  config : agent_config;
  mutable state : agent_state;
  mutable messages : message list;
  mutable action_count : int;
  context : (string, string) Hashtbl.t;
}

(* Utility Functions *)
let generate_id () =
  let time = Unix.gettimeofday () in
  let random = Random.int 1000000 in
  Printf.sprintf "msg_%.0f_%d" time random

let current_timestamp () = Unix.gettimeofday ()

(* Message Creation *)
let create_message role content =
  {
    id = generate_id ();
    role;
    content;
    timestamp = current_timestamp ();
    metadata = [];
  }

(* Agent Creation *)
let create_agent config =
  {
    config;
    state = Idle;
    messages = [];
    action_count = 0;
    context = Hashtbl.create 16;
  }

(* State Management *)
let set_state agent new_state =
  agent.state <- new_state

let get_state agent = agent.state

let add_message agent message =
  agent.messages <- message :: agent.messages

let get_messages agent = List.rev agent.messages

(* Context Management *)
let set_context agent key value =
  Hashtbl.replace agent.context key value

let get_context agent key =
  Hashtbl.find_opt agent.context key

(* Action Execution *)
let execute_action action =
  match action with
  | Execute (cmd, args) ->
      let cmd_str = String.concat " " (cmd :: args) in
      (* Simulate command execution *)
      Success (Printf.sprintf "Executed: %s" cmd_str)
  
  | ReadFile path ->
      try
        let content = In_channel.with_open_text path In_channel.input_all in
        Success content
      with
      | Sys_error msg -> Failure (Printf.sprintf "Failed to read %s: %s" path msg)
  
  | WriteFile (path, content) ->
      try
        Out_channel.with_open_text path (fun oc ->
          Out_channel.output_string oc content
        );
        Success (Printf.sprintf "Wrote %d bytes to %s" (String.length content) path)
      with
      | Sys_error msg -> Failure (Printf.sprintf "Failed to write %s: %s" path msg)
  
  | HttpRequest (method_str, url, headers) ->
      (* Simulate HTTP request *)
      Success (Printf.sprintf "HTTP %s request to %s with %d headers" method_str url (List.length headers))
  
  | Search (pattern, scope) ->
      (* Simulate search *)
      Success (Printf.sprintf "Searching for '%s' in %s" pattern scope)
  
  | Think reasoning ->
      Success (Printf.sprintf "[Thinking] %s" reasoning)

(* Agent Processing *)
let process_message agent message =
  if agent.action_count >= agent.config.max_actions then
    Lwt.return (Failure "Maximum action count exceeded")
  else
    let* () = Lwt.return () in
    set_state agent (Processing message.content);
    add_message agent message;
    
    (* Simulate processing *)
    let response = create_message Assistant 
      (Printf.sprintf "Processed: %s (Action count: %d/%d)" 
         message.content 
         agent.action_count 
         agent.config.max_actions) in
    
    agent.action_count <- agent.action_count + 1;
    set_state agent Idle;
    Lwt.return (Success response.content)

(* Agent Lifecycle *)
let start_agent agent =
  set_state agent Idle;
  Printf.printf "Agent %s v%s started\n" agent.config.name agent.config.version;
  Lwt.return_unit

let stop_agent agent =
  set_state agent Idle;
  Printf.printf "Agent %s stopped\n" agent.config.name;
  Lwt.return_unit

(* Advanced Features *)
let with_timeout timeout_seconds f =
  Lwt.catch
    (fun () ->
      let* result = f () in
      Lwt.return (Ok result))
    (fun exn ->
      Lwt.return (Error (Printexc.to_string exn)))

let chain_actions actions =
  let rec execute_chain acc = function
    | [] -> Lwt.return (Success (String.concat "\n" (List.rev acc)))
    | action :: rest ->
        let* result = Lwt.return (execute_action action) in
        match result with
        | Success output -> execute_chain (output :: acc) rest
        | Failure msg -> Lwt.return (Failure msg)
        | Partial (out, err) -> execute_chain (Printf.sprintf "%s\n[Error: %s]" out err :: acc) rest
  in
  execute_chain [] actions
