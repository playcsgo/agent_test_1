from agents import Runner, trace, gen_trace_id
from search_agent import search_agent
from planner_agent import planner_agent, WebSearchItem, WebSearchPlan
from writer_agent import writer_agent, ReportData
from email_agent import email_agent
import asyncio

class ResearchManager:

    async def run(self, query:str):
        print('string searching...')
        trace_id = gen_trace_id()
        with trace("Reserch trace", trace_id=trace_id):
            yield(f"View trace: https://platform.openai.com/traces/trace?trace_id={trace_id}")
            search_plan = await self.plan_searches(query)
            yield "Search Plan done, start to search..."
            search_results = await self.perfrom_searches(search_plan)
            yield "Search Completed, writting report..."
            report = await self.write_report(query, search_results)
            yield 'Report written, sending email...'
            await self.send_email(report)
            yield 'Email sent, please check.  process completed.'
            yield report.markdown_report




    async def plan_searches(self, query:str) -> WebSearchPlan:
        print('planning...')
        result = await Runner.run(planner_agent, f"Query: {query}")
        print(f"Will perform {len(result.final_output.searches)} searches")
        return result.final_output_as(WebSearchPlan)
    
    async def perfrom_searches(self, search_plan: WebSearchPlan) -> list[str]:
        print('searching...')
        completed_number = 0
        tasks = [
            asyncio.create_task(self.search(item))
            for item in search_plan.searches
            ]
        
        results = []
        for task in asyncio.as_completed(tasks):
            result = await task
            if result is not None:
                results.append(result)
            completed_number += 1
            print(f"Searching... {completed_number}/{len(tasks)} completed")
        print("Searching finished")
        
        return results
    
    async def search(self, item: WebSearchItem) -> str | None:
        input = f'Search term: {item.query}\n Reason for searching: {item.reason}'
        try:
            result = await Runner.run(
                search_agent,
                input,
            )
            return str(result.final_output)
        except Exception:
            return None
        
    async def write_report(self, query: str, search_results: list[str]) -> ReportData:
        print('Writing Report...')
        input = f'Original Query: {query}\n Summary of search: {search_results}'
        result = await  Runner.run(writer_agent, input)
        print('Report Writing done.')

        return result.final_output_as(ReportData)
    
    async def send_email(self, report: ReportData) -> None:
        print('Generating Email....')
        result = await Runner.run(email_agent, report.markdown_report)
        print('Email Sent')
        return report
    