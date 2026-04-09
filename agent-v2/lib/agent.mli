(* Agent v2 - Interface Module *)
(* Public API for the agent framework *)

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
  | Execute of string * string list
  | ReadFile of string
  | WriteFile of string * string
  | HttpRequest of string * string * (string * string) list
  | Search of string * string
  | Think of string

type action_result =
  | Success of string
  | Failure of string
  | Partial of string * string

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

type agent

(* Creation *)
val create_agent : agent_config -> agent
val create_message : message_role -> string -> message
val generate_id : unit -> string
val current_timestamp : unit -> float

(* State Management *)
val set_state : agent -> agent_state -> unit
val get_state : agent -> agent_state
val add_message : agent -> message -> unit
val get_messages : agent -> message list

(* Context *)
val set_context : agent -> string -> string -> unit
val get_context : agent -> string -> string option

(* Actions *)
val execute_action : action -> action_result
val process_message : agent -> message -> action_result Lwt.t
val chain_actions : action list -> action_result Lwt.t

(* Lifecycle *)
val start_agent : agent -> unit Lwt.t
val stop_agent : agent -> unit Lwt.t
val with_timeout : float -> (unit -> 'a Lwt.t) -> ('a, string) result Lwt.t
