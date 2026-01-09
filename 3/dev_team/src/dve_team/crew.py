from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List


@CrewBase
class DveTeam():
    """DveTeam crew"""

    agents: List[BaseAgent]
    tasks: List[Task]

    @agent
    def leader(self) -> Agent:
        return Agent(
            config=self.agents_config['leader'], # type: ignore[index]
            verbose=True
        )

    @agent
    def backend(self) -> Agent:
        return Agent(
            config=self.agents_config['backend'], # type: ignore[index]
            verbose=True,
            allow_code_execution=True,
            code_execution_mode='safe',
            max_execution_time=500,
            max_retry_limit=3
        )
    
    @agent
    def frontend(self) -> Agent:
        return Agent(
            config=self.agents_config['frontend'], # type: ignore[index]
            verbose=True,
        )
    
    @agent
    def tester(self) -> Agent:
        return Agent(
            config=self.agents_config['tester'], # type: ignore[index]
            verbose=True,
        )


    @task
    def design_task(self) -> Task:
        return Task(
            config=self.tasks_config['design_task'], # type: ignore[index]
        )

    @task
    def code_task(self) -> Task:
        return Task(
            config=self.tasks_config['code_task'], # type: ignore[index]
        )
    
    @task
    def frontend_task(self) -> Task:
        return Task(
            config=self.tasks_config['frontend_task'], # type: ignore[index]
        )
    
    @task
    def test_task(self) -> Task:
        return Task(
            config=self.tasks_config['test_task'], # type: ignore[index]
        )

    @crew
    def crew(self) -> Crew:
        """Creates the DveTeam crew"""

        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
