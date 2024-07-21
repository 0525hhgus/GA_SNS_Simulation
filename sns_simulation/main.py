import pandas as pd
from config import LLM_NAME, API_KEY, PATH, num_agent, persona_list
from sns_functions import  SNS_Simulation

df_init_posts = pd.read_csv(PATH+"/_neologism_data_0524 - _filtered data.csv")

def post_format(x):
    return f'{x["Post"]}\n{x["Meaning"]}\n{x["Origin/Usage"]}'

init_posts = df_init_posts.apply(post_format, axis=1).to_list()

simulation = SNS_Simulation(num_agents=num_agent, persona_list=persona_list, cycle_count=0)

for content in init_posts:
    simulation.db.add_post(cycle_id=0, writer_id=99, content=content)

simulation.db.save_to_csv()
posts = pd.read_csv(PATH + "/posts.csv")

# init neologism simulation
for agent in simulation.agents:
    agent.reaction = 'read'
    agent.process_activities()

simulation.db.save_to_csv()
simulation.save_agents_to_csv(PATH+'/agent_info.csv')

# simulation
df_posts = pd.read_csv(PATH+"/posts.csv")
df_comments = pd.read_csv(PATH+"/comments.csv")
df_agents = pd.read_csv(PATH+'/agent_info.csv')

simulation = SNS_Simulation(num_agents=num_agent, persona_list=persona_list, cycle_count=0)

simulation.db.load_from_csv(PATH+"/posts.csv", PATH+"/comments.csv")
simulation.load_agents_from_csv(PATH+'/agent_info.csv')

simulation.run_simulation(0, 30)
simulation.display_simulation()
simulation.db.save_to_csv()
simulation.save_agents_to_csv(PATH+'/agent_info.csv')