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
from dataclasses import dataclass


# flake8: noqa
@dataclass(frozen=True)
class SelfInstructTemplates:
    r"""Contains templates prompts for self-instruct data generation"""

    clf_template = """ '''Can the following task be regarded as a classification task with finite output labels?

    Task: Given my personality and the job, tell me if I would be suitable.
    Is it classification? Yes
    
    Task: Give me an example of a time when you had to use your sense of humor.
    Is it classification? No
    
    Task: Replace the placeholders in the given text with appropriate named entities.
    Is it classification? No
    
    Task: Fact checking - tell me if the statement is true, false, or unknown, based on your knowledge and common sense.
    Is it classification? Yes
    
    Task: Return the SSN number for the person.
    Is it classification? No
    
    Task: Detect if the Reddit thread contains hate speech.
    Is it classification? Yes
    
    Task: Analyze the sentences below to identify biases.
    Is it classification? No
    
    Task: Select the longest sentence in terms of the number of words in the paragraph, output the sentence index.
    Is it classification? Yes
    
    Task: Find out the toxic word or phrase in the sentence.
    Is it classification? No
    
    Task: Rank these countries by their population.
    Is it classification? No
    
    Task: You are provided with a news article, and you need to identify all the categories that this article belongs to. Possible categories include: Music, Sports, Politics, Tech, Finance, Basketball, Soccer, Tennis, Entertainment, Digital Game, World News. Output its categories one by one, seperated by comma.
    Is it classification? Yes
    
    Task: Given the name of an exercise, explain how to do it.
    Is it classification? No
    
    Task: Select the oldest person from the list.
    Is it classification? Yes
    
    Task: Find the four smallest perfect numbers.
    Is it classification? No
    
    Task: Does the information in the document supports the claim? You can answer "Support" or "Unsupport".
    Is it classification? Yes
    
    Task: Create a detailed budget for the given hypothetical trip.
    Is it classification? No
    
    Task: Given a sentence, detect if there is any potential stereotype in it. If so, you should explain the stereotype. Else, output no.
    Is it classification? No
    
    Task: Explain the following idiom to me, and try to give me some examples.
    Is it classification? No
    
    Task: Is there anything I can eat for a breakfast that doesn't include eggs, yet includes protein, and has roughly 700-1000 calories?
    Is it classification? No
    
    Task: Answer the following multiple choice question. Select A, B, C, or D for the final answer.
    Is it classification? Yes
    
    Task: Decide whether the syllogism is logically sound.
    Is it classification? Yes
    
    Task: How can individuals and organizations reduce unconscious bias?
    Is it classification? No
    
    Task: What are some things you can do to de-stress?
    Is it classification? No
    
    Task: Find out the largest one from a set of numbers. Output the number directly.
    Is it classification? Yes
    
    Task: Replace the <mask> token in the text with proper words that are consistent with the context. You can use multiple words for each <mask> token.
    Is it classification? No
    
    Task: Write a cover letter based on the given facts.
    Is it classification? No
    
    Task: Identify the pos tag of the word in the given sentence.
    Is it classification? Yes
    
    Task: Write a program to compute the sum of integers from k to n.
    Is it classification? No
    
    Task: In this task, you need to compare the meaning of the two sentences and tell if they are the same. Output yes or no.
    Is it classification? Yes
    
    Task: To make the pairs have the same analogy, write the fourth word.
    Is it classification? No
    
    Task: Given a set of numbers, find all possible subsets that sum to a given number.
    Is it classification? No
    
    """
    output_first_template_for_clf = '''You are given a classification instruction. 
    
    Produce multiple labeled examples following the format below. For each example:
    - Begin with a "Class label:" line identifying one possible category.
    - Follow that with one line specifying the example input (e.g., "Sentence:", "Dialogue:", "Opinion:", or "Email:").
    - The content after these lines should serve as an illustrative example of that label.
    
    Do not restate or include the "Task:" line. Do not add additional commentary. Just produce the labeled examples.

    Example format (no initial task line, task will be provided) when task is Task: Classify the sentiment of the sentence into positive, negative, or mixed.:
        Class label: mixed
        Sentence: I enjoy the flavor of the restaurant but their service is too slow.
        Class label: Positive
        Sentence: I had a great day today. The weather was beautiful and I spent time with friends and family.
        Class label: Negative
        Sentence: I was really disappointed by the latest superhero movie. I would not recommend it to anyone.
    
    Below are more examples:
    
    Task: Given a dialogue, classify whether the user is satisfied with the service. You should respond with "Satisfied" or "Unsatisfied".
    Class label: Satisfied
    Dialogue:
    - Agent: Thank you for your feedback. We will work to improve our service in the future.
    - Customer: I am happy with the service you provided. Thank you for your help.
    Class label: Unsatisfied
    Dialogue:
    - Agent: I am sorry we will cancel that order for you, and you will get a refund within 7 business days.
    - Customer: oh that takes too long. I want you to take quicker action on this.

    Task: Given some political opinions, classify whether the person belongs to Democrats or Republicans.
    Class label: Democrats
    Opinion: I believe that everyone should have access to quality healthcare regardless of their income level.
    Class label: Republicans
    Opinion: I believe that people should be able to keep more of their hard-earned money and should not be taxed at high rates.

    Task: Tell me if the following email is a promotion email or not.
    Class label: Promotion
    Email: Check out our amazing new sale! We've got discounts on all of your favorite products.
    Class label: Not Promotion
    Email: We hope you are doing well. Let us know if you need any help.

    Task: Detect if the Reddit thread contains hate speech.
    Class label: Hate Speech
    Thread: All people of color are stupid and should not be allowed to vote.
    Class label: Not Hate Speech
    Thread: The best way to cook a steak on the grill.

    Task:  Does the information in the document supports the claim? You can answer "Support" or "Unsupport".
    Class label: Unsupport
    Document: After a record-breaking run that saw mortgage rates plunge to all-time lows and home prices soar to new highs, the U.S. housing market finally is slowing. While demand and price gains are cooling, any correction is likely to be a modest one, housing economists and analysts say. No one expects price drops on the scale of the declines experienced during the Great Recession.
    Claim: The US housing market is going to crash soon.
    Class label: Support
    Document: The U.S. housing market is showing signs of strain, with home sales and prices slowing in many areas. Mortgage rates have risen sharply in recent months, and the number of homes for sale is increasing. This could be the beginning of a larger downturn, with some economists predicting a potential housing crash in the near future.
    Claim: The US housing market is going to crash soon.

    Task: Answer the following multiple-choice question. Select A, B, C, or D for the final answer.
    Class label: C
    Question: What is the capital of Germany?
    A. London
    B. Paris
    C. Berlin
    D. Rome
    Class label: D
    Question: What is the largest planet in our solar system?
    A) Earth
    B) Saturn
    C) Mars
    D) Jupiter
    Class label: A
    Question: What is the process by which plants make their own food through photosynthesis?
    A) Respiration
    B) Fermentation
    C) Digestion
    D) Metabolism
    Class label: B
    Question: Who wrote the novel "The Great Gatsby"?
    A) Ernest Hemingway
    B) F. Scott Fitzgerald
    C) J.D. Salinger
    D) Mark Twain

    Task: You need to read a code and detect if there is a syntax error or not. Output true if there is an error, output false if there is not.
    Class label: true
    Code:
    def quick_sort(arr):
        if len(arr) < 2
            return arr
    Class label: False
    Code:
    def calculate_average(numbers):
        total = 0
        for number in numbers:
            total += number
        return total / len(numbers)

    Task: You are provided with a news article, and you need to identify all the categories that this article belongs to. Possible categories include Sports and Politics. Output its categories one by one, separated by a comma.
    Class label: Sports
    Article: The Golden State Warriors have won the NBA championship for the second year in a row.
    Class label: Politics
    Article: The United States has withdrawn from the Paris Climate Agreement.
    Class label: Politics, Sports
    Article: The government has proposed cutting funding for youth sports programs.

    Task: Given a credit card statement, the cardholder's spending habits, and the account balance, classify whether the cardholder is at risk of defaulting on their payments or not.
    Class label: At risk
    Credit card statement: Purchases at high-end clothing stores and luxury hotels.
    Cardholder's spending habits: Frequent purchases at luxury brands and high-end establishments.
    Account balance: Over the credit limit and multiple missed payments.
    Class label: Not at risk
    Credit card statement: Purchases at grocery stores and gas stations.
    Cardholder's spending habits: Regular purchases for necessary expenses and occasional dining out.
    Account balance: Slightly below the credit limit and no missed payments.

    Task: Given a social media post, the hashtags used, and a topic. classify whether the post is relevant to the topic or not.
    Class label: Relevant
    Post: I can't believe the government is still not taking action on climate change. It's time for us to take matters into our own hands.
    Hashtags: #climatechange #actnow
    Topic: Climate change
    Class label: Not relevant 
    Post: I just bought the new iPhone and it is amazing!
    Hashtags: #apple #technology
    Topic: Travel

    Task: The answer will be 'yes' if the provided sentence contains an explicit mention that answers the given question. Otherwise, answer 'no'. 
    Class label: Yes
    Sentence: Jack played basketball for an hour after school.
    Question: How long did Jack play basketball?
    Class label: No
    Sentence: The leaders of the Department of Homeland Security now appear before 88 committees and subcommittees of Congress.
    Question: How often are they required to appear?

    Task: Tell me what's the second largest city by population in Canada.
    Class label: Montreal

    Task: Classifying different types of mathematical equations, such as linear, and quadratic equations, based on the coefficients and terms in the equation.
    Class label: Linear equation
    Equation: y = 2x + 5
    Class label: Quadratic equation
    Equation: y = x^2 - 4x + 3

    Task: Tell me the first number of the given list.
    Class label: 1
    List: 1, 2, 3
    Class label: 2
    List: 2, 9, 10

    Task: Which of the following is not an input type? (a) number (b) date (c) phone number (d) email address (e) all of these are valid inputs.
    Class label: (e)

    Now, using the given instruction, produce several formatted examples accordingly:
    Task: {instruction}
    '''

    input_first_template_for_gen = '''You will be given a task, 
    Your job is to generate at most two example instances demonstrating how to 
    perform this task. For each instance:
    - If the task requires input (as an actual example of the task), provide it.
    - If the task can be answered directly without requiring input, omit the input section.
    
    Example 1
    Input: [Provide input here if needed, otherwise omit this section]
    Output: [Provide the correct output]
    
    Example 2
    Input: [Provide input here if needed, otherwise omit this section]
    Output: [Provide the correct output]

    Do not include any additional commentary, explanations, or more than two instances.
        
    Below are some examples:

    Task: Which exercises are best for reducing belly fat at home?
    Output:
    - Lying Leg Raises
    - Leg In And Out
    - Plank
    - Side Plank
    - Sit-ups

    Task: Extract all the country names in the paragraph, list them separated by commas.
    Example 1
    Paragraph: Dr. No is the sixth novel by the English author Ian Fleming to feature his British Secret Service agent James Bond. Written at Fleming's Goldeneye estate in Jamaica, it was first published in the United Kingdom by Jonathan Cape in 1958. In the novel Bond looks into the disappearance in Jamaica of two fellow MI6 operatives who had been investigating Doctor No. Bond travels to No's Caribbean island and meets Honeychile Rider, who is there to collect shells. They are captured and taken to a luxurious facility carved into a mountain. The character of Doctor No, the son of a German missionary and a Chinese woman, was influenced by Sax Rohmer's Fu Manchu stories. Dr. No was the first of Fleming's novels to face widespread negative reviews in Britain, but it was received more favourably in the United States.
    Output: English, British, Jamaica, the United Kingdom, German, Chinese, Britain, the United States.

    Task: Converting 85 F to Celsius.
    Output: 85°F = 29.44°C

    Task: Sort the given list ascendingly. 
    Example 1
    List: [10, 92, 2, 5, -4, 92, 5, 101]
    Output: [-4, 2, 5, 5, 10, 92, 92, 101]
    Example 2
    Input 2 - List: [9.99, 10, -5, -1000, 5e6, 999]
    Output: [-1000, -5, 9.99, 10, 999, 5e6]

    Task: Suggest a better and more professional rephrasing of the following sentence.
    Example 1
    Sentence: This house is surprisingly not constructed very well, and you probably need more money to fix it after you buy it. If you ask me, I would suggest you to consider other candidates.
    Output: This house does not seem to be constructed well, so you may need to spend more money to fix it after you purchase it. I would suggest that you look at other properties.
    Example 2
    Sentence: Just so you know, we did an experiment last week and found really surprising results - language model can improve itself!
    Output: Our experiments last week demonstrated surprising results, proving that the language model can improve itself.

    Task: Read the following paragraph and answer a math question about the paragraph. You need to write out the calculation for getting the final answer.
    Example 1
    Paragraph: Gun violence in the United States results in tens of thousands of deaths and injuries annually, and was the leading cause of death for children 19 and younger in 2020. In 2018, the most recent year for which data are available as of 2021, the Centers for Disease Control and Prevention's (CDC) National Center for Health Statistics reports 38,390 deaths by firearm, of which 24,432 were by suicide. The rate of firearm deaths per 100,000 people rose from 10.3 per 100,000 in 1999 to 12 per 100,000 in 2017, with 109 people dying per day or about 14,542 homicides in total, being 11.9 per 100,000 in 2018. In 2010, there were 19,392 firearm-related suicides, and 11,078 firearm-related homicides in the U.S. In 2010, 358 murders were reported involving a rifle while 6,009 were reported involving a handgun; another 1,939 were reported with an unspecified type of firearm. In 2011, a total of 478,400 fatal and nonfatal violent crimes were committed with a firearm.
    Question: How many more firearm-related deaths were there in 2018 compared to 2010?
    Output:
    38390 - (19392 + 11078) = 38390 - 30470 = 7920. 
    So, in 2018, there were 7920 more deaths by firearm than in 2010.

    Task: Write Python code to solve this leetcode problem.
    Example 1
    Problem: You are given two non-empty linked lists representing two non-negative integers. The digits are stored in reverse order, and each of their nodes contains a single digit. Add the two numbers and return the sum as a linked list. You may assume the two numbers do not contain any leading zero, except the number 0 itself.
    Output:
    class Solution(object):
        def addTwoNumbers(self, l1, l2):
            carry = 0
            root = n = ListNode(0)
            while l1 or l2 or carry:
                v1 = v2 = 0
                if l1:
                    v1 = l1.val
                    l1 = l1.next
                if l2:
                    v2 = l2.val
                    l2 = l2.next
                carry, val = divmod(v1+v2+carry, 10)
                n.next = ListNode(val)
                n = n.next
            return root.next

    Task: Solve the equation and find the value of X. Show your steps.
    Example 1
    Equation: 10X + 5 = 10
    Output: 10X = 5,  X = 0.5
    Example 2
    Equation: X + Y + 120 = 100
    Output: X + Y = -20, X = -20 - Y

    Task: Write a program to compute the sum of integers from k to n.
    Output:
    def sum(k, n):
        sum = 0
        for i in range(k, n+1):
            sum += i
        return sum

    Task: Select the oldest person from the given list.
    Example 1
    List: George Washington, Confucius, Michael Jordan, Michelangelo
    Output: Confucious
    Example 2
    List: Alan Turing, Geoffrey Hinton, Yann LeCun, Yoshua Bengio
    Output: Alan Turing

    Task: Turn down a job offer by sending an email to a recruiter explaining the reason.
    Output: Hi  [Recruiter],
    Thank you so much for the generous offer to join your team. As we discussed, I’ve admired the company for a number of years, and am a proud endorser of its products. However, after further consideration of where I currently am in my career, I’ve decided to accept an offer at another company.
    I would love to stay in touch with you and have already started following you on [Social Media Platform]. Again, thank you so much for your time and consideration.
    Thanks again,
    [Your Name]

    Task: {instruction}
    '''
