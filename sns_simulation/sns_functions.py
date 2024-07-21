import requests
import google.generativeai as genai
from openai import OpenAI
import openai
import os
import csv
import time
import random
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from config import LLM_NAME, API_KEY, PATH

if LLM_NAME == "Meta-Llama-3-70B-Instruct" or LLM_NAME == "Meta-Llama-3-8B-Instruct":
    hf_token = API_KEY

    API_URL = "https://api-inference.huggingface.co/models/meta-llama/" + LLM_NAME
    headers = {"Authorization": "Bearer "+hf_token}

    def query(payload):
        try:
            response = requests.post(API_URL, headers=headers, json=payload)
            time.sleep(10)
            response.raise_for_status()
            data = response.json()
            generated_text = data[0].get('generated_text', '')
            return data
        except (KeyError, IndexError, requests.RequestException) as e:
            print(f"An error occurred: {str(e)}")
            return [{'generated_text': ''}]

elif LLM_NAME == "gpt4o" or LLM_NAME == "gpt-3.5-turbo":
    # 환경 변수로 OpenAI API 키 설정
    os.environ['OPENAI_API_KEY'] = API_KEY
    openai.api_key = API_KEY

    def query(payload):
        try:
            client = OpenAI()
            parameters = payload.get("parameters", {})
            max_new_tokens = parameters.get("max_new_tokens")
            temperature = parameters.get("temperature", 0.9)  # 기본값 0.9
            top_p = parameters.get("top_p")

            inputs = payload["inputs"].strip().split('\n')
            system_content = '\n'.join(inputs[:-1]).strip()
            user_content = inputs[-1].strip()

            api_params = {
                "model": LLM_NAME,
                "messages": [
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": user_content}
                ],
                "max_tokens": max_new_tokens,
                "n": 1,
                "stop": None,
                "temperature": temperature,
            }

            if top_p is not None:
                api_params["top_p"] = top_p

            response = client.chat.completions.create(**api_params)
            time.sleep(10)
            reply = response.choices[0].message.content
            return [{'generated_text': reply}]
        except openai.OpenAIError as e:
            print(f"An error occurred: {str(e)}")
            return [{'generated_text': ''}]

elif LLM_NAME == "gemini-1.5-pro" or LLM_NAME == "gemini-1.0-pro":
    os.environ['GOOGLE_API_KEY'] = API_KEY
    genai.configure(api_key=API_KEY)

    def query(payload):
        try:
            parameters = payload.get("parameters", {})
            max_new_tokens = parameters.get("max_new_tokens")
            temperature = parameters.get("temperature", 0.9)  # 기본값 0.9
            top_p = parameters.get("top_p")

            generation_config = genai.GenerationConfig(max_output_tokens=max_new_tokens, temperature=temperature,
                                                       top_p=top_p)

            model = genai.GenerativeModel(LLM_NAME, generation_config=generation_config)  # 1.0은 gemini-1.0-pro

            response = model.generate_content(payload["inputs"])
            time.sleep(10)

            reply = response.text
            return [{'generated_text': reply}]
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            return [{'generated_text': ''}]

class PostTable:
    def __init__(self):
        self.posts = []

    def add_post(self, cycle_id, writer_id, content):
        post_id = len(self.posts)
        self.posts.append({'writer_id': writer_id, 'id': post_id, 'cycle_id': cycle_id, 'content': content})
        return post_id

    def find_post(self, post_id):
        for post in self.posts:
            if post['id'] == post_id:
                return post
        return None

    def get_all_posts(self):
        return self.posts

class CommentTable:
    def __init__(self):
        self.comments = []

    def add_comment(self, cycle_id, post_id, commenter_id, content):
        comment_id = len(self.comments)
        comment_detail = {
            'comment_id': comment_id,
            'cycle_id': cycle_id,
            'post_id': post_id,
            'agent_id': commenter_id,
            'content': content
        }
        self.comments.append(comment_detail)

    def get_comments_for_post(self, post_id):
        return [comment for comment in self.comments if comment['post_id'] == post_id]


class PostDatabase:
    def __init__(self):
        self.posts = PostTable()
        self.comments = CommentTable()

    def add_post(self, cycle_id, writer_id, content):
        return self.posts.add_post(cycle_id, writer_id, content)

    def add_comment(self, cycle_id, post_id, commenter_id, content):
        self.comments.add_comment(cycle_id, post_id, commenter_id, content)

    def get_all_posts(self):
        return self.posts.get_all_posts()

    def get_comments_for_post(self, post_id):
        return self.comments.get_comments_for_post(post_id)

    def save_to_csv(self):
        with open(PATH+'/posts.csv', 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['Post ID', 'Writer ID', 'Cycle ID','Content'])
            for post in self.posts.get_all_posts():
                writer.writerow([post['id'], post['writer_id'], post['cycle_id'], post['content']])

        with open(PATH+'/comments.csv', 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['Comment ID', 'Post ID', 'Agent ID', 'Cycle ID', 'Content'])
            for comment in self.comments.comments:
                writer.writerow([comment['comment_id'], comment['post_id'], comment['agent_id'], comment['cycle_id'], comment['content']])

    def load_from_csv(self, post_path, comment_path):
        posts = []
        with open(post_path, 'r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                self.posts.add_post(int(row['Cycle ID']),int(row['Writer ID']),row['Content'])

        comments = []
        with open(comment_path, 'r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                self.add_comment(int(row['Cycle ID']),int(row['Post ID']),int(row['Agent ID']), row['Content'])


class Agent:
    def __init__(self, id, db, persona, cycle_count=0, reaction='read', read_posts=None, commented_posts=None, memory='', sns_statistics=None):
        self.id = id
        self.db = db
        self.persona = persona
        self.reaction = reaction
        self.read_posts = read_posts if read_posts is not None else set()
        self.commented_posts = commented_posts if commented_posts is not None else set()
        self.cycle_count = cycle_count
        self.memory = memory
        self.sns_statistics = sns_statistics if sns_statistics is not None else {
            'read': 0,
            'write': 0,
            'comment': 0
        }

    def update_status(self):

        self.cycle_count += 1

        self.reaction = self.decide_read_write()

        if 'write' in self.reaction:
            self.reaction = 'write'
            self.sns_statistics['write'] += 1
            self.display_status()
            self.make_post(self.generate_post())

        else:
            self.reaction = 'read'
            self.process_activities()


    def process_activities(self):
        posts = self.db.get_all_posts()
        self.display_status()

        for post in posts:
            self.summarize_memory()
            if post['id'] not in self.read_posts:
                self.reaction = self.decide_action(post)
                print("decide_action")
                self.display_status()
                if 'read' in self.reaction:
                    self.reaction = 'read'
                    self.sns_statistics['read'] += 1
                    self.read_posts.add(post['id'])
                    self.read_new_posts(post)
                elif 'comment' in self.reaction:
                    self.reaction = 'comment'
                    self.sns_statistics['comment'] += 1
                    self.read_posts.add(post['id'])
                    self.read_new_posts(post)
                    self.comment_on_post(post['id'], self.generate_comment(post['content']))
                else:
                    self.reaction = 'read'
                    self.read_posts.add(post['id'])
                    self.read_new_posts(post)

    def decide_read_write(self):
        output = query({"inputs": "You are an SNS user with the following <persona>, <memory>, and <SNS activity statistics>. \n" +
                        "<persona>: " + self.persona + "\n" +
                        "<memory>: " + self.memory + "\n" +
                        "<SNS activity statistics>: number of posts written " + str(self.sns_statistics['write']) + " times, number of reactions (one of comment, share, read, comment and share): " + str(self.sns_statistics['read']) +
                        "You must keep the appropriate number of posts written and number of reactions considering the persona. Considering your persona, memory, and SNS activity statistics, you must select **only one word** for <your action> from ['write', 'read'] in the following <example output> format. \n" +
                        "example output:\n" +
                        "<your action>: read\n" +
                        "<your action>: write\n" +
                        "<your action>: write\n" +
                        "<your action>: read\n" +
                        "<your action>: ",
                    "parameters": {
                    "return_full_text": False,
                    "max_new_tokens": 3,
                "temperature": 0.9,
                "top_p": 0.9}})

        reply = output[0]['generated_text']
        print(reply)

        return reply

    def decide_action(self, post):
        output = query({"inputs": "You are an SNS user with the following <persona> and <memory>. \n" +
                        "<persona>: " + self.persona + "\n" +
                        "<memory>: " + self.memory + "\n" +
                        "<post>: " + post['content'] + "\n" +
                        "Considering your persona and memory, you must select **only one word** for <your reaction> to the <post> from ['comment', 'read'] in the following <example output> format. \n" +
                        "example output:\n" +
                        "<your reaction>: comment\n" +
                        "<your reaction>: read\n" +
                        "<your reaction>: comment\n" +
                        "<your reaction>: read\n" +
                        "<your reaction>: ",
                    "parameters": {
                    "return_full_text": False,
                    "max_new_tokens": 3,
                "temperature": 0.9,
                    "top_p": 0.9}})

        reply = output[0]['generated_text']
        print(reply)

        return reply

    def make_post(self, content):
        post_id = self.db.add_post(self.cycle_count, self.id, content)
        self.read_posts.add(post_id)
        self.summarize_post(content)
        self.memory += '\n'

        print(f"Agent {self.id} posted: {content}")

    def read_new_posts(self, post):
            self.summarize_post(post['content'])
            self.memory += '\n'

            print(f"Agent {self.id} read post {post['id']} by Agent {post['writer_id']}: {post['content']}")


    def generate_post(self):
        output = query({"inputs": "You are an SNS user. Considering the following <persona> and <memory>, please write <your post> within 100 characters. \n" +
                        "<persona>: " + self.persona + "\n" +
                        "<memory>: " + self.memory + "\n" +
                        "<your post>: ",
                "parameters": {
                "return_full_text": False,
                "max_new_tokens": 40,
                "temperature": 0.9,
                    "top_p": 0.9}})

        reply = output[0]['generated_text']

        if reply == '':
            return self.memory
        else:
            return reply


    def generate_comment(self, post_content):
        output = query({"inputs": "You are an SNS user with the following <persona> and <memory>. \n" +
                        "<persona>: " + self.persona + "\n" +
                        "<memory>: " + self.memory + "\n" +
                        "Please write <your SNS comment> on the following <post> within 50 characters. \n" +
                        "<post>: " + post_content + "\n" +
                        "<your SNS comment>: ",
                    "parameters": {
                    "return_full_text": False,
                    "max_new_tokens": 20,
                "temperature": 0.9,
                    "top_p": 0.9}})

        reply = output[0]['generated_text']

        if reply == '':
            return self.memory
        else:
            return reply

    def comment_on_post(self, post_id, comment_content):
        if post_id not in self.commented_posts:
            self.db.add_comment(self.cycle_count, post_id, self.id, comment_content)
            self.commented_posts.add(post_id)
            self.summarize_comment(comment_content)
            self.memory += '\n'

            print(f"Agent {self.id} commented on post {post_id}: {comment_content}")

    def summarize_memory(self):
        if self.memory != '' and len(self.memory) > 1000:
            print("(((summarize_memory)))")
            output = query({"inputs": "You are an SNS user with the following <persona> and <memory>. \n" +
                                    "<persona>: " + self.persona + "\n" +
                                    "<memory>: " + self.memory + "\n" +
                                    "Summarize the important contents in <memory> up to 500 characters. \n" +
                                    "<memory>: ",
                                    "parameters": {
                                    "return_full_text": False,
                                    "max_new_tokens": 100,
                "temperature": 0.9,
                    "top_p": 0.9}})
            reply = output[0]['generated_text']

            if reply != '':
                self.memory = reply

    def summarize_post(self, post_content):
        self.memory += "\n[READ POST]"
        self.memory += post_content

    def summarize_comment(self, comment_content):
        self.memory += "[COMMENT]"
        self.memory += comment_content


    def display_status(self):
        print("------------------------------------------------")
        print(f"Agent {self.id} Status Report:")
        print(f"  Reaction Mode: {self.reaction}")
        print(f"  Read Posts IDs: {sorted(list(self.read_posts))}")
        print(f"  Commented on Posts IDs: {sorted(list(self.commented_posts))}")
        print(f"  Memory: {self.memory}")
        print("------------------------------------------------")


class SNS_Simulation:
    def __init__(self, num_agents, persona_list, cycle_count):
        self.db = PostDatabase()
        self.agents = [Agent(i, self.db, persona_list[i], cycle_count) for i in range(num_agents)]

    def run_simulation(self, start_round, end_round):
        for r in range(start_round, end_round):
            print(f"=========== Round {r+1} ===========")
            for agent in self.agents:
                agent.update_status()
                # agent.display_status()
                agent.summarize_memory()

    def save_agents_to_csv(self, filepath):
        with open(filepath, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file, quotechar='"', quoting=csv.QUOTE_MINIMAL)
            writer.writerow([
                'Agent ID', 'Reaction Mode', 'Read Posts IDs', 'Commented Posts IDs', 'Persona', 'Memory',
                'Cycle Count', 'Read Count', 'Write Count', 'Comment Count'
            ])
            for agent in self.agents:
                writer.writerow([
                agent.id,
                agent.reaction,
                ','.join(map(str, sorted(list(agent.read_posts)))),
                ','.join(map(str, sorted(list(agent.commented_posts)))),
                agent.persona,
                agent.memory,
                agent.cycle_count,
                agent.sns_statistics['read'],
                agent.sns_statistics['write'],
                agent.sns_statistics['comment']
                ])

    def load_agents_from_csv(self, filepath):
        agents = []
        with open(filepath, 'r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                agent_id = int(row['Agent ID'])
                reaction_mode = row['Reaction Mode']
                read_posts_ids = set(map(int, row['Read Posts IDs'].split(','))) if row['Read Posts IDs'] else set()
                commented_posts_ids = set(map(int, row['Commented Posts IDs'].split(','))) if row['Commented Posts IDs'] else set()
                persona = row['Persona']
                memory = row['Memory']
                cycle_count = int(row['Cycle Count'])
                sns_statistics = {
                    'read': int(row['Read Count']),
                    'write': int(row['Write Count']),
                    'comment': int(row['Comment Count'])
                }
                agents.append(Agent(agent_id, self.db, persona, cycle_count, reaction_mode, read_posts_ids, commented_posts_ids, memory, sns_statistics))
        self.agents = agents

    def display_simulation(self):
        console = Console()
        all_posts = self.db.get_all_posts()
        for post in all_posts:
            # Create a text object for the post content
            post_content = Text(f"Post ID {post['id']} by Agent {post['writer_id']}:\n'{post['content']}'", style="bold green")
            # Gather comments for this post
            comments = self.db.get_comments_for_post(post['id'])
            comments_text = Text()
            if comments:
                comments_text.append("\n\nComments:\n", style="bold magenta")
                for comment in comments:
                    comments_text.append(f"Agent {comment['agent_id']} says: '{comment['content']}'\n", style="bold cyan")
            else:
                comments_text.append("\n\nNo comments yet.", style="italic red")

            # Combine post and comments in one panel
            combined_text = Text.assemble(post_content, comments_text)
            panel = Panel(combined_text, title=f"[bold magenta]Post ID {post['id']} by Agent {post['writer_id']}[/]", expand=False)
            console.print(panel)