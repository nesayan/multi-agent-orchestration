from agents.subagent_internet_search.subagent_internet_search import get_internet_search_workflow
from agents.subagent_mathematics.subagent_mathematics import get_mathematics_workflow
from agents.master import get_master_agent
from agents.masterV2 import get_masterV2_agent

import logging

logger = logging.getLogger(__name__)

# Add imports and call the agent loader here
async def load_all_agents():
    logger.info("Loading all agents...")
    
    await get_internet_search_workflow()
    await get_mathematics_workflow()
    # await get_master_agent()    # Loading master V1

    await get_masterV2_agent()  # Loading master V2


    logger.info("All agents loaded successfully")
