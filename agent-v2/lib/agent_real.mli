(* Agent v2 - REAL Production Agent Interface *)

(** {1 Types} *)

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

type http_method = GET | POST | PUT | DELETE | PATCH

type action =
  | Execute of string * string list
  | ReadFile of string
  | WriteFile of string * string
  | HttpRequest of http_method * string * (string * string) list * string option
  | Search of string * string
  | Think of string
  | CodeAnalysis of string
  | Git of string * string list

type action_result =
  | Success of string
  | Failure of string
  | Partial of string * string

type agent_state =
  | Idle
  | Processing of string
  | Executing of action
  | Error of string

type log_level = Debug | Info | Warning | Error

type agent_config = {
  id : agent_id;
  name : string;
  version : string;
  max_actions : int;
  timeout_seconds : float;
  enable_thinking : bool;
  working_dir : string;
  log_level : log_level;
}

type agent

type session_summary = {
  agent_id : string;
  name : string;
  version : string;
  start_time : float;
  message_count : int;
  action_count : int;
  context : (string * string) list;
  final_state : string;
}

(** {1 Configuration} *)

val create_config :
  ?max_actions:int ->
  ?timeout:float ->
  ?thinking:bool ->
  ?working_dir:string ->
  ?log_level:log_level ->
  string -> string -> string -> agent_config

(** {1 Agent Lifecycle} *)

val create_agent : agent_config -> agent
val start_agent : agent -> unit Lwt.t
val stop_agent : agent -> unit Lwt.t
val get_state : agent -> agent_state
val export_session : agent -> session_summary

(** {1 Messaging} *)

val create_message : message_role -> string -> message
val process_message : agent -> message -> action_result Lwt.t
val add_message : agent -> message -> unit
val get_messages : agent -> message list

(** {1 Actions} *)

val execute_action : agent -> action -> action_result Lwt.t
val execute_actions_batch : agent -> action list -> action_result Lwt.t

(** {1 Context} *)

val set_context : agent -> string -> string -> unit
val get_context : agent -> string -> string option
val get_all_context : agent -> (string * string) list

(** {1 Logging} *)

val log : agent -> log_level -> string -> unit
val get_logs : agent -> (float * log_level * string) list

(** {1 Utilities} *)

val generate_id : unit -> string
val current_timestamp : unit -> float
