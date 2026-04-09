(* Agent v2 - Test Suite *)
(* Unit tests for the agent framework *)

open Agent

let test_create_agent () =
  let config = {
    id = "test_agent";
    name = "Test Agent";
    version = "1.0.0";
    max_actions = 5;
    timeout_seconds = 10.0;
    enable_thinking = false;
  } in
  let agent = create_agent config in
  assert (get_state agent = Idle);
  assert (List.length (get_messages agent) = 0);
  Printf.printf "✓ test_create_agent passed\n"

let test_create_message () =
  let msg = create_message User "Hello" in
  assert (msg.role = User);
  assert (msg.content = "Hello");
  assert (String.length msg.id > 0);
  assert (msg.timestamp > 0.0);
  Printf.printf "✓ test_create_message passed\n"

let test_context_management () =
  let config = {
    id = "test_agent";
    name = "Test";
    version = "1.0.0";
    max_actions = 5;
    timeout_seconds = 10.0;
    enable_thinking = false;
  } in
  let agent = create_agent config in
  set_context agent "key1" "value1";
  assert (get_context agent "key1" = Some "value1");
  assert (get_context agent "nonexistent" = None);
  Printf.printf "✓ test_context_management passed\n"

let test_message_history () =
  let config = {
    id = "test_agent";
    name = "Test";
    version = "1.0.0";
    max_actions = 5;
    timeout_seconds = 10.0;
    enable_thinking = false;
  } in
  let agent = create_agent config in
  let msg1 = create_message User "First" in
  let msg2 = create_message Assistant "Second" in
  add_message agent msg1;
  add_message agent msg2;
  let messages = get_messages agent in
  assert (List.length messages = 2);
  assert ((List.hd messages).content = "First");
  Printf.printf "✓ test_message_history passed\n"

let test_execute_action () =
  let think_action = Think "Test reasoning" in
  (match execute_action think_action with
  | Success result -> 
      assert (String.contains result '[Thinking]');
      Printf.printf "✓ test_execute_action passed\n"
  | _ -> failwith "Think action should succeed")

let test_state_transitions () =
  let config = {
    id = "test_agent";
    name = "Test";
    version = "1.0.0";
    max_actions = 5;
    timeout_seconds = 10.0;
    enable_thinking = false;
  } in
  let agent = create_agent config in
  assert (get_state agent = Idle);
  set_state agent (Processing "test");
  assert (get_state agent = Processing "test");
  set_state agent Idle;
  assert (get_state agent = Idle);
  Printf.printf "✓ test_state_transitions passed\n"

let run_all_tests () =
  Printf.printf "\n=== Agent v2 Test Suite ===\n\n";
  test_create_agent ();
  test_create_message ();
  test_context_management ();
  test_message_history ();
  test_execute_action ();
  test_state_transitions ();
  Printf.printf "\n✅ All tests passed!\n\n"

let () = run_all_tests ()
