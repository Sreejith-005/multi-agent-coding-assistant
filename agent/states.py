from pydantic import BaseModel, Field


class PlannedFile(BaseModel):
    path: str = Field(description="Relative file path, e.g. 'index.html' or 'app/main.py'")
    purpose: str = Field(description="One sentence: what this file is responsible for")


class Plan(BaseModel):
    name: str = Field(description="Short project name in kebab-case, e.g. 'calculator-app'")
    description: str = Field(description="One paragraph describing the app")
    techstack: str = Field(description="Languages, frameworks and libraries to use")
    features: list[str] = Field(description="User-visible features")
    files: list[PlannedFile] = Field(description="Every file the project needs")


class ImplementationTask(BaseModel):
    filepath: str = Field(description="Relative path of the file to write")
    task_description: str = Field(
        description="Detailed instructions: functions/classes/ids to create, "
        "what to import from other files, expected behaviour"
    )


class TaskPlan(BaseModel):
    implementation_steps: list[ImplementationTask] = Field(
        description="Ordered tasks, one per file, dependencies first"
    )
