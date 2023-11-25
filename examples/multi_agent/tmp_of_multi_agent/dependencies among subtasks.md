
<span style='color: blue;'>Dependencies among subtasks: {</span>

<span style='color: blue;'>    &quot;subtask 1&quot;: {</span>

<span style='color: blue;'>        &quot;description&quot;: &quot;- Write Chapter 1: Dawn of the Star Chaser, setting the interstellar political scene and introducing the crew.&quot;,</span>

<span style='color: blue;'>        &quot;dependencies&quot;: [],</span>

<span style='color: blue;'>        &quot;input_tags&quot;: [</span>

<span style='color: blue;'>            &quot;&#x27;Interstellar Political Landscape&#x27;&quot;,</span>

<span style='color: blue;'>            &quot;&#x27;Character Profiles&#x27;&quot;,</span>

<span style='color: blue;'>            &quot;&#x27;Mission Objectives&#x27;&quot;</span>

<span style='color: blue;'>        ],</span>

<span style='color: blue;'>        &quot;input_content&quot;: &quot;- Information on interstellar political entities, character profiles, and mission objectives.&quot;,</span>

<span style='color: blue;'>        &quot;output_standard&quot;: &quot;- Chapter 1 is completed when it introduces the political landscape, main characters, and mission briefing.&quot;</span>

<span style='color: blue;'>    },</span>

<span style='color: blue;'>    &quot;subtask 2&quot;: {</span>

<span style='color: blue;'>        &quot;description&quot;: &quot;- Write Chapter 2: First Leap, capturing the ship&#x27;s first FTL jump and the crew&#x27;s reactions to anomalies.&quot;,</span>

<span style='color: blue;'>        &quot;dependencies&quot;: [</span>

<span style='color: blue;'>            &quot;subtask 1&quot;</span>

<span style='color: blue;'>        ],</span>

<span style='color: blue;'>        &quot;input_tags&quot;: [</span>

<span style='color: blue;'>            &quot;&#x27;Spaceship Technology&#x27;&quot;,</span>

<span style='color: blue;'>            &quot;&#x27;Initial Challenges&#x27;&quot;,</span>

<span style='color: blue;'>            &quot;&#x27;Early Discoveries&#x27;&quot;</span>

<span style='color: blue;'>        ],</span>

<span style='color: blue;'>        &quot;input_content&quot;: &quot;- Details on spaceship technology and descriptions of initial challenges and discoveries.&quot;,</span>

<span style='color: blue;'>        &quot;output_standard&quot;: &quot;- Chapter 2 is completed when the maiden voyage and initial challenges are vividly described.&quot;</span>

<span style='color: blue;'>    },</span>

<span style='color: blue;'>    &quot;subtask 3&quot;: {</span>

<span style='color: blue;'>        &quot;description&quot;: &quot;- Write Chapter 3: Echoes of Novada, exploring the planet&#x27;s society and the crew&#x27;s secret agendas.&quot;,</span>

<span style='color: blue;'>        &quot;dependencies&quot;: [</span>

<span style='color: blue;'>            &quot;subtask 2&quot;</span>

<span style='color: blue;'>        ],</span>

<span style='color: blue;'>        &quot;input_tags&quot;: [</span>

<span style='color: blue;'>            &quot;&#x27;Novada Society&#x27;&quot;,</span>

<span style='color: blue;'>            &quot;&#x27;Crew&#x27;s Secret Agendas&#x27;&quot;</span>

<span style='color: blue;'>        ],</span>

<span style='color: blue;'>        &quot;input_content&quot;: &quot;- Cultural and societal information of Novada and insights into crew members&#x27; personal missions.&quot;,</span>

<span style='color: blue;'>        &quot;output_standard&quot;: &quot;- Chapter 3 is completed when it provides a detailed exploration of Novada and reveals crew secrets.&quot;</span>

<span style='color: blue;'>    },</span>

<span style='color: blue;'>    &quot;subtask 4&quot;: {</span>

<span style='color: blue;'>        &quot;description&quot;: &quot;- Write Chapter 4: Shadows Over Zelin, depicting the tension within the crew and Zelin&#x27;s military environment.&quot;,</span>

<span style='color: blue;'>        &quot;dependencies&quot;: [</span>

<span style='color: blue;'>            &quot;subtask 3&quot;</span>

<span style='color: blue;'>        ],</span>

<span style='color: blue;'>        &quot;input_tags&quot;: [</span>

<span style='color: blue;'>            &quot;&#x27;Zelin&#x27;s Military Society&#x27;&quot;,</span>

<span style='color: blue;'>            &quot;&#x27;Crew&#x27;s Ideological Conflicts&#x27;&quot;</span>

<span style='color: blue;'>        ],</span>

<span style='color: blue;'>        &quot;input_content&quot;: &quot;- Information on Zelin&#x27;s military society and the crew&#x27;s conflicting ideologies.&quot;,</span>

<span style='color: blue;'>        &quot;output_standard&quot;: &quot;- Chapter 4 is completed when it portrays the military environment of Zelin and the crew&#x27;s internal strife.&quot;</span>

<span style='color: blue;'>    },</span>

<span style='color: blue;'>    &quot;subtask 5&quot;: {</span>

<span style='color: blue;'>        &quot;description&quot;: &quot;- Write Chapter 5: Through the Eye of the Storm, leading to the climactic confrontation.&quot;,</span>

<span style='color: blue;'>        &quot;dependencies&quot;: [</span>

<span style='color: blue;'>            &quot;subtask 4&quot;</span>

<span style='color: blue;'>        ],</span>

<span style='color: blue;'>        &quot;input_tags&quot;: [</span>

<span style='color: blue;'>            &quot;&#x27;Climactic Showdown&#x27;&quot;,</span>

<span style='color: blue;'>            &quot;&#x27;Character Sacrifices&#x27;&quot;,</span>

<span style='color: blue;'>            &quot;&#x27;Interstellar Dynamics&#x27;&quot;</span>

<span style='color: blue;'>        ],</span>

<span style='color: blue;'>        &quot;input_content&quot;: &quot;- Descriptions of the showdown, character sacrifices, and the resulting shift in interstellar dynamics.&quot;,</span>

<span style='color: blue;'>        &quot;output_standard&quot;: &quot;- Chapter 5 is completed when the showdown and its consequences are compellingly presented.&quot;</span>

<span style='color: blue;'>    },</span>

<span style='color: blue;'>    &quot;subtask 6&quot;: {</span>

<span style='color: blue;'>        &quot;description&quot;: &quot;- Write Chapter 6: A New Beginning, reflecting on the journey and hinting at future adventures.&quot;,</span>

<span style='color: blue;'>        &quot;dependencies&quot;: [</span>

<span style='color: blue;'>            &quot;subtask 5&quot;</span>

<span style='color: blue;'>        ],</span>

<span style='color: blue;'>        &quot;input_tags&quot;: [</span>

<span style='color: blue;'>            &quot;&#x27;Journey Reflections&#x27;&quot;,</span>

<span style='color: blue;'>            &quot;&#x27;Unresolved Mysteries&#x27;&quot;,</span>

<span style='color: blue;'>            &quot;&#x27;Closing Note&#x27;&quot;</span>

<span style='color: blue;'>        ],</span>

<span style='color: blue;'>        &quot;input_content&quot;: &quot;- Reflections on the journey&#x27;s outcomes, unresolved mysteries, and a closing note for future narratives.&quot;,</span>

<span style='color: blue;'>        &quot;output_standard&quot;: &quot;- Chapter 6 is completed when it provides a reflective conclusion and teases future directions.&quot;</span>

<span style='color: blue;'>    }</span>

<span style='color: blue;'>}</span>
