from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
from pydantic import BaseModel, Field
from crewai_tools import SerperDevTool
from crewai.memory import LongTermMemory, ShortTermMemory, EntityMemory
from crewai.memory.storage.rag_storage import RAGStorage
from crewai.memory.storage.ltm_sqlite_storage import LTMSQLiteStorage

class TrendingCompany(BaseModel):
    name: str = Field(description='Company Name')
    ticker: str = Field(description='Stock ticker symbol')
    reason: str = Field(description='Reason this company is trending in the news')

class TrendingCompanyList(BaseModel):
    companies: List[TrendingCompany]

class TrendingCompanyResearch(BaseModel):
    name: str = Field(description='Company Name')
    market_position: str = Field(description='Current market position and competitive analysis')
    future_outlook: str = Field(description='Future outlook and growth prospects')
    investment_potential: str = Field(description='Investment potential and suitability for investment')

class TrendingCompanyReseachList(BaseModel):
    research_list: List[TrendingCompanyResearch] = Field(description='Research of all Trending Companies')


@CrewBase
class StockPicker():
    """StockPicker crew"""

    agents: List[BaseAgent]
    tasks: List[Task]

    @agent
    def trending_company_finder(self) -> Agent:
        return Agent(
            config=self.agents_config['trending_company_finder'], # type: ignore[index]
            tools=[SerperDevTool()],
            memory=True
        )

    @agent
    def financial_researcher(self) -> Agent:
        return Agent(
            config=self.agents_config['financial_researcher'], # type: ignore[index]
        )
    
    @agent
    def stock_picker(self) -> Agent:
        return Agent(
            config=self.agents_config['stock_picker'], # type: ignore[index]
            verbose=True,
            memory=True,
        )
    

    @task
    def find_trending_companies(self) -> Task:
        return Task(
            config=self.tasks_config['find_trending_companies'],
            output_pydantic=TrendingCompanyList
        )

    @task
    def research_trending_companies(self) -> Task:
        return Task(
            config=self.tasks_config['research_trending_companies'],
           output_pydantic=TrendingCompanyReseachList
        )
    
    @task
    def pick_best_company(self) -> Task:
        return Task(
            config=self.tasks_config['pick_best_company'],
        )
    


    @crew
    def crew(self) -> Crew:
        """Creates the StockPicker crew"""

        manager = Agent(
            config = self.agents_config['manager'],
            allow_delegation=True,
            verbose=True,
        )


        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.hierarchical, ## allow manager delegate tasks
            manager_agent=manager,
            memory=True,
            # Long-term memory for persistent storage across sessions
            long_term_memory=LongTermMemory(
                storage=LTMSQLiteStorage(
                    db_path='./memory/long_term_memory_storage.db'
                )
            ),

            # Short-term memory for current context using RAG
            short_term_memory=ShortTermMemory(
                storage = RAGStorage(
                    embedder_config = {
                        'provider': 'openai',
                        'config': {
                            'model': 'text-embedding-3-small',
                        }
                    },
                    type='short_term',
                    path='./memory/'
                )
            ),

            # Entity memory for tracking key information about entities
            entity_memory=EntityMemory(
                storage = RAGStorage(
                    embedder_config= {
                        'provider': 'openai',
                        'config': {
                            'model': 'text-embedding-3-small'
                        }
                    },
                    type='short_term',
                    path='./memory/'
                )
            )
        )
