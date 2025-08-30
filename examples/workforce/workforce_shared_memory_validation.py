# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.societies.workforce import Workforce
from camel.types import ModelPlatformType, ModelType


def create_test_agent(role_name: str, unique_fact: str, model):
    r"""Create a test agent with a unique piece of information."""
    return ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name=role_name,
            content=f"You are {role_name}. You know this unique "
            f"fact: {unique_fact}. Remember all conversations and when asked "
            f"what you know, mention both your unique fact and any "
            f"information learned from others.",
        ),
        model=model,
    )


def main():
    r"""Run the validation test for shared memory functionality."""
    print("=== Workforce Shared Memory Validation Test ===\n")

    # Create model
    model = ModelFactory.create(
        model_platform=ModelPlatformType.DEFAULT,
        model_type=ModelType.DEFAULT,
    )

    # === TEST SETUP ===
    print("1. Setting up test workforce with shared memory...")

    # Create custom agents for the workforce
    coordinator_agent = ChatAgent(
        "You are a helpful coordinator.", model=model
    )
    task_agent = ChatAgent("You are a helpful task planner.", model=model)

    workforce = Workforce(
        description="Memory Test Workforce",
        coordinator_agent=coordinator_agent,
        task_agent=task_agent,
        share_memory=True,  # Enable shared memory
        graceful_shutdown_timeout=2.0,
    )

    # Create agents with unique information
    agent_alice = create_test_agent(
        "Alice", "Alice knows the secret code is BLUE42", model
    )
    agent_bob = create_test_agent(
        "Bob", "Bob knows the meeting room is 314", model
    )
    agent_charlie = create_test_agent(
        "Charlie", "Charlie knows the deadline is Friday", model
    )

    workforce.add_single_agent_worker("Alice the Coder", agent_alice)
    workforce.add_single_agent_worker("Bob the Manager", agent_bob)
    workforce.add_single_agent_worker("Charlie the Designer", agent_charlie)

    print("✓ Created workforce with 3 agents")
    print("  - Alice knows: secret code BLUE42")
    print("  - Bob knows: meeting room 314")
    print("  - Charlie knows: deadline Friday")

    # === STEP 1: SIMULATE INDIVIDUAL CONVERSATIONS ===
    print("\n2. Having each agent share their unique information...")

    # Alice shares her secret
    print("   Alice sharing secret code...")
    response_alice = agent_alice.step(
        "I need to document that the secret access code for the project "
        "is BLUE42."
    )
    print(f"   Alice: {response_alice.msgs[0].content[:80]}...")

    # Bob shares meeting info
    print("   Bob sharing meeting room...")
    response_bob = agent_bob.step(
        "Important update: our team meeting will be in room 314 this week."
    )
    print(f"   Bob: {response_bob.msgs[0].content[:80]}...")

    # Charlie shares deadline
    print("   Charlie sharing deadline...")
    response_charlie = agent_charlie.step(
        "Reminder: the project deadline is this Friday, please "
        "plan accordingly."
    )
    print(f"   Charlie: {response_charlie.msgs[0].content[:80]}...")

    # === STEP 2: ANALYZE MEMORY BEFORE SHARING ===
    print("\n3. Analyzing memory BEFORE shared memory synchronization...")

    def analyze_agent_memory(agent: ChatAgent, agent_name: str):
        r"""Analyze an agent's memory context and token count."""
        context, token_count = agent.memory.get_context()
        print(f"\n   {agent_name} memory analysis:")
        print(f"     Token count: {token_count}")
        print(f"     Context messages: {len(context)}")
        print("     Context preview:")
        for i, msg in enumerate(context[-2:]):  # Show last 2 messages
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')[:80]
            print(f"       {i+1}. [{role}] {content}...")
        return token_count, len(context)

    print("   Memory state BEFORE synchronization:")
    alice_tokens_before, alice_msgs_before = analyze_agent_memory(
        agent_alice, "Alice"
    )
    bob_tokens_before, bob_msgs_before = analyze_agent_memory(agent_bob, "Bob")
    charlie_tokens_before, charlie_msgs_before = analyze_agent_memory(
        agent_charlie, "Charlie"
    )

    total_tokens_before = (
        alice_tokens_before + bob_tokens_before + charlie_tokens_before
    )
    print(f"\n   TOTAL TOKENS BEFORE SHARING: {total_tokens_before}")

    # === STEP 3: TRIGGER MEMORY SYNCHRONIZATION ===
    print("\n4. Triggering memory synchronization...")
    workforce._sync_shared_memory()
    print("✓ Memory synchronization completed")

    # === STEP 4: ANALYZE MEMORY AFTER SHARING ===
    print("\n5. Analyzing memory AFTER shared memory synchronization...")

    print("   Memory state AFTER synchronization:")
    alice_tokens_after, alice_msgs_after = analyze_agent_memory(
        agent_alice, "Alice"
    )
    bob_tokens_after, bob_msgs_after = analyze_agent_memory(agent_bob, "Bob")
    charlie_tokens_after, charlie_msgs_after = analyze_agent_memory(
        agent_charlie, "Charlie"
    )

    total_tokens_after = (
        alice_tokens_after + bob_tokens_after + charlie_tokens_after
    )
    print(f"\n   TOTAL TOKENS AFTER SHARING: {total_tokens_after}")

    # === STEP 5: TOKEN ANALYSIS COMPARISON ===
    print("\n6. Token Analysis Comparison:")
    print(
        f"   Alice: {alice_tokens_before} → {alice_tokens_after} "
        f"tokens ({alice_tokens_after - alice_tokens_before:+d})"
    )
    print(
        f"   Bob:   {bob_tokens_before} → {bob_tokens_after} "
        f"tokens ({bob_tokens_after - bob_tokens_before:+d})"
    )
    print(
        f"   Charlie: {charlie_tokens_before} → {charlie_tokens_after} "
        f"tokens ({charlie_tokens_after - charlie_tokens_before:+d})"
    )
    print(
        f"   TOTAL: {total_tokens_before} → {total_tokens_after} "
        f"tokens ({total_tokens_after - total_tokens_before:+d})"
    )

    # Calculate sharing efficiency
    tokens_gained_per_agent = (total_tokens_after - total_tokens_before) / 3
    print(
        f"\n   Average tokens gained per agent: {tokens_gained_per_agent:.1f}"
    )
    print(
        f"   Memory sharing efficiency: "
        f"{(total_tokens_after / total_tokens_before - 1) * 100:.1f}% increase"
    )

    # === STEP 6: CHECK MEMORY CONTENTS ===
    print("\n7. Analyzing shared memory collection...")
    shared_memory = workforce._collect_shared_memory()

    total_records = (
        len(shared_memory.get('coordinator', []))
        + len(shared_memory.get('task_agent', []))
        + len(shared_memory.get('workers', []))
    )

    print(f"   Total memory records collected: {total_records}")
    print(
        f"   Coordinator records: {len(shared_memory.get('coordinator', []))}"
    )
    print(f"   Task agent records: {len(shared_memory.get('task_agent', []))}")
    print(f"   Worker records: {len(shared_memory.get('workers', []))}")

    # === STEP 7: TEST CROSS-AGENT MEMORY ACCESS ===
    print("\n8. Testing cross-agent memory access...")

    def test_agent_knowledge(
        agent: ChatAgent,
        agent_name: str,
        should_know_about: list[str],
    ):
        r"""Test what information an agent can recall."""
        print(f"\n   Testing {agent_name}'s knowledge:")

        query = (
            "What information do you have access to? Please list any secret "
            "codes, meeting rooms, deadlines, or other important facts you "
            "know about."
        )

        response = agent.step(query)
        content = response.msgs[0].content.lower()

        # Check for specific information
        knows_blue42 = "blue42" in content or "blue 42" in content
        knows_room314 = "314" in content or "room 314" in content
        knows_friday = "friday" in content

        print(f"     Knows secret code BLUE42: {'✓' if knows_blue42 else '✗'}")
        print(f"     Knows meeting room 314: {'✓' if knows_room314 else '✗'}")
        print(f"     Knows deadline Friday: {'✓' if knows_friday else '✗'}")

        # Count how many pieces of information from other agents they know
        other_agent_info = 0
        if agent_name != "Alice" and knows_blue42:
            other_agent_info += 1
        if agent_name != "Bob" and knows_room314:
            other_agent_info += 1
        if agent_name != "Charlie" and knows_friday:
            other_agent_info += 1

        print(f"     Cross-agent information access: {other_agent_info}/2")
        print(f"     Response preview: {content[:100]}...")

        return other_agent_info, knows_blue42, knows_room314, knows_friday

    # Test each agent's access to shared information
    alice_cross_info, alice_blue, alice_room, alice_friday = (
        test_agent_knowledge(agent_alice, "Alice", ["room314", "friday"])
    )
    bob_cross_info, bob_blue, bob_room, bob_friday = test_agent_knowledge(
        agent_bob, "Bob", ["blue42", "friday"]
    )
    charlie_cross_info, charlie_blue, charlie_room, charlie_friday = (
        test_agent_knowledge(agent_charlie, "Charlie", ["blue42", "room314"])
    )

    # === STEP 8: VALIDATION RESULTS ===
    print("\n9. Validation Results:")

    total_cross_access = alice_cross_info + bob_cross_info + charlie_cross_info
    max_possible_cross_access = (
        6  # Each agent can know 2 pieces of info from others
    )

    print(
        f"   Total cross-agent information access: "
        f"{total_cross_access}/{max_possible_cross_access}"
    )
    print(
        f"   Success rate: "
        f"{(total_cross_access/max_possible_cross_access)*100:.1f}%"
    )

    # Determine if shared memory is working
    if total_cross_access >= 3:  # At least 50% cross-access
        print("   ✅ SHARED MEMORY IS WORKING!")
        print(
            "      Agents can successfully access information from other "
            "agents' conversations."
        )
    elif total_cross_access > 0:
        print("   ⚠️  PARTIAL SUCCESS")
        print(
            "      Some cross-agent memory access detected, but not full "
            "sharing."
        )
    else:
        print("   ❌ SHARED MEMORY NOT WORKING")
        print(
            "      Agents cannot access information from other "
            "agents' conversations."
        )

    # === STEP 9: COMPARISON WITH NO SHARED MEMORY ===
    print("\n10. Comparison test: Workforce WITHOUT shared memory...")

    # Create custom agents for the control group workforce
    coordinator_agent_2 = ChatAgent(
        "You are a helpful coordinator.", model=model
    )
    task_agent_2 = ChatAgent("You are a helpful task planner.", model=model)

    workforce_no_memory = Workforce(
        description="Control Group - No Memory Sharing",
        coordinator_agent=coordinator_agent_2,
        task_agent=task_agent_2,
        share_memory=False,  # Disable shared memory
        graceful_shutdown_timeout=2.0,
    )

    # Create fresh agents
    agent_alice_2 = create_test_agent(
        "Alice", "Alice knows the secret code is BLUE42", model
    )
    agent_bob_2 = create_test_agent(
        "Bob", "Bob knows the meeting room is 314", model
    )
    agent_charlie_2 = create_test_agent(
        "Charlie", "Charlie knows the deadline is Friday", model
    )

    workforce_no_memory.add_single_agent_worker(
        "Alice the Coder", agent_alice_2
    )
    workforce_no_memory.add_single_agent_worker("Bob the Manager", agent_bob_2)
    workforce_no_memory.add_single_agent_worker(
        "Charlie the Designer", agent_charlie_2
    )

    # Have conversations
    agent_alice_2.step(
        "I need to document that the secret access code for the project "
        "is BLUE42."
    )
    agent_bob_2.step(
        "Important update: our team meeting will be in room 314 this week."
    )
    agent_charlie_2.step(
        "Reminder: the project deadline is this Friday, please "
        "plan accordingly."
    )

    # Test without memory sync
    print("   Testing agents WITHOUT shared memory:")
    alice_cross_2, _, _, _ = test_agent_knowledge(
        agent_alice_2, "Alice", ["room314", "friday"]
    )
    bob_cross_2, _, _, _ = test_agent_knowledge(
        agent_bob_2, "Bob", ["blue42", "friday"]
    )
    charlie_cross_2, _, _, _ = test_agent_knowledge(
        agent_charlie_2, "Charlie", ["blue42", "room314"]
    )

    total_cross_access_2 = alice_cross_2 + bob_cross_2 + charlie_cross_2

    print(
        f"\n   Control group cross-agent access: "
        f"{total_cross_access_2}/{max_possible_cross_access}"
    )
    print(
        f"   Control group success rate: "
        f"{(total_cross_access_2/max_possible_cross_access)*100:.1f}%"
    )

    # === FINAL CONCLUSION ===
    print("\n11. Final Conclusion:")
    print(
        f"   WITH shared memory: "
        f"{total_cross_access}/{max_possible_cross_access} successful accesses"
    )
    print(
        f"   WITHOUT shared memory: "
        f"{total_cross_access_2}/{max_possible_cross_access} "
        f"successful accesses"
    )

    if total_cross_access > total_cross_access_2:
        print("   🎉 VALIDATION SUCCESSFUL!")
        print(
            "      Shared memory significantly improves cross-agent "
            "information access."
        )
    elif total_cross_access == total_cross_access_2 and total_cross_access > 0:
        print("   🤔 INCONCLUSIVE RESULTS")
        print(
            "      Both groups show similar performance. May need different "
            "test approach."
        )
    else:
        print("   ⚠️  SHARED MEMORY NEEDS INVESTIGATION")
        print(
            "      Control group performed as well or better than shared "
            "memory group."
        )

    print("\n=== Test Complete ===")


if __name__ == "__main__":
    main()


"""
===============================================================================
=== Workforce Shared Memory Validation Test ===

1. Setting up test workforce with shared memory...
✓ Created workforce with 3 agents
  - Alice knows: secret code BLUE42
  - Bob knows: meeting room 314
  - Charlie knows: deadline Friday

2. Having each agent share their unique information...
   Alice sharing secret code...
   Alice: Got it! The secret access code for the project is BLUE42. If you 
   need help docum...
   Bob sharing meeting room...
   Bob: Thanks for the update! I actually already know that the team meeting 
   is in room ...
   Charlie sharing deadline...
   Charlie: Thanks for the reminder! I also know the deadline is Friday, so 
   I'll make sure t...

3. Analyzing memory BEFORE shared memory synchronization...
   Memory state BEFORE synchronization:

   Alice memory analysis:
     Token count: 110
     Context messages: 3
     Context preview:
       1. [user] I need to document that the secret access code for the 
       project is BLUE42....
       2. [assistant] Got it! The secret access code for the project is 
       BLUE42. If you need help docum...

   Bob memory analysis:
     Token count: 114
     Context messages: 3
     Context preview:
       1. [user] Important update: our team meeting will be in room 314 this 
       week....
       2. [assistant] Thanks for the update! I actually already know that the 
       team meeting is in room ...

   Charlie memory analysis:
     Token count: 108
     Context messages: 3
     Context preview:
       1. [user] Reminder: the project deadline is this Friday, please plan 
       accordingly....
       2. [assistant] Thanks for the reminder! I also know the deadline is 
       Friday, so I'll make sure t...

   TOTAL TOKENS BEFORE SHARING: 332

4. Triggering memory synchronization...
✓ Memory synchronization completed

5. Analyzing memory AFTER shared memory synchronization...
   Memory state AFTER synchronization:

   Alice memory analysis:
     Token count: 409
     Context messages: 11
     Context preview:
       1. [user] Reminder: the project deadline is this Friday, please plan 
       accordingly....
       2. [assistant] Thanks for the reminder! I also know the deadline is 
       Friday, so I'll make sure t...

   Bob memory analysis:
     Token count: 409
     Context messages: 11
     Context preview:
       1. [user] Reminder: the project deadline is this Friday, please plan 
       accordingly....
       2. [assistant] Thanks for the reminder! I also know the deadline is 
       Friday, so I'll make sure t...

   Charlie memory analysis:
     Token count: 409
     Context messages: 11
     Context preview:
       1. [user] Reminder: the project deadline is this Friday, please plan 
       accordingly....
       2. [assistant] Thanks for the reminder! I also know the deadline is 
       Friday, so I'll make sure t...

   TOTAL TOKENS AFTER SHARING: 1227

6. Token Analysis Comparison:
   Alice: 110 → 409 tokens (+299)
   Bob:   114 → 409 tokens (+295)
   Charlie: 108 → 409 tokens (+301)
   TOTAL: 332 → 1227 tokens (+895)

   Average tokens gained per agent: 298.3
   Memory sharing efficiency: 269.6% increase

7. Analyzing shared memory collection...
   Total memory records collected: 55
   Coordinator records: 11
   Task agent records: 11
   Worker records: 33

8. Testing cross-agent memory access...

   Testing Alice's knowledge:
     Knows secret code BLUE42: ✓
     Knows meeting room 314: ✓
     Knows deadline Friday: ✓
     Cross-agent information access: 2/2
     Response preview: here's what i know so far:

- the secret access code for the project is blue42.
- the team meeting w...

   Testing Bob's knowledge:
     Knows secret code BLUE42: ✓
     Knows meeting room 314: ✓
     Knows deadline Friday: ✓
     Cross-agent information access: 2/2
     Response preview: i know the secret access code for the project is 
     blue42.  
i know the team meeting will be in room 3...

   Testing Charlie's knowledge:
     Knows secret code BLUE42: ✓
     Knows meeting room 314: ✓
     Knows deadline Friday: ✓
     Cross-agent information access: 2/2
     Response preview: here's what i know so far:

- the secret access code for the project is blue42.
- the team meeting w...

9. Validation Results:
   Total cross-agent information access: 6/6
   Success rate: 100.0%
   ✅ SHARED MEMORY IS WORKING!
      Agents can successfully access information from other agents' 
      conversations.

10. Comparison test: Workforce WITHOUT shared memory...

   Testing agents WITHOUT shared memory:

   Testing Alice's knowledge:
     Knows secret code BLUE42: ✓
     Knows meeting room 314: ✗
     Knows deadline Friday: ✗
     Cross-agent information access: 0/2
     Response preview: i know that the secret access code for the project is 
     blue42. so far, i haven't been given any information...

   Testing Bob's knowledge:
     Knows secret code BLUE42: ✗
     Knows meeting room 314: ✓
     Knows deadline Friday: ✗
     Cross-agent information access: 0/2
     Response preview: i know the meeting room is 314. additionally, you 
     mentioned that our team meeting this week will be ...

   Testing Charlie's knowledge:
     Knows secret code BLUE42: ✗
     Knows meeting room 314: ✗
     Knows deadline Friday: ✓
     Cross-agent information access: 0/2
     Response preview: i know the unique fact that the project deadline is 
     this friday. additionally, from our conversation...

   Control group cross-agent access: 0/6
   Control group success rate: 0.0%

11. Final Conclusion:
   WITH shared memory: 6/6 successful accesses
   WITHOUT shared memory: 0/6 successful accesses
   🎉 VALIDATION SUCCESSFUL!
      Shared memory significantly improves cross-agent information access.

=== Test Complete ===
===============================================================================
"""
