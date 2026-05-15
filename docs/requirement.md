# Coding Challenge: Case

# Timeline

## Overview

Build a Case Timeline view that gives receiving clinicians a fast, structured picture
of a patient's state at shift change. For this challenge, we are looking for you to
build a Case Timeline: a chronological view of case events — from presenting
complaint through diagnostics, treatments, and current plan — that lets an
incoming clinician orient quickly without re-reading full notes.

In this exercise, you will build an end-to-end feature: given a plain-text veterinary
medical transcript, extract and render a structured timeline of the consultation.

## Technical Requirements

```
Backend: Python + FastAPI
Frontend: React + TypeScript
AI / Prompt layer:BAML for LLM interactions
You may use any storage and other service support infra you prefer
You may use any additional libraries you find appropriate.
You may use AI coding agents Cursor, Claude Code, Copilot, etc.) — this is
encouraged
```

## What You're Building

### Core Flow

User pastes a plain-text medical transcript into the UI, triggers timeline generation
and in a few seconds a case timeline appears.

Each event should include a title and a more detailed 1 2 sentence description of
what that event entailed.

### The Timeline View

Each event in the timeline should display:

```
Event type
History: Discussion of the presenting complaint and the history of the
present illness
Physical Exam: Physical examination performed by the doctor.
Vitals: Any vital signs taken during the consult
Diagnostic: Diagnostics discussed during the consult. Capture whether
they were approved or declined.
Treatment: Treatments discussed during the consult. Capture whether
they were approved or described.
Recommendations: Vaccines, medications, diet, and follow-up
Title — short label for the event
Description — supporting detail drawn from the transcript
Status badge — e.g. Completed, Pending, In Progress (where applicable)
```

The timeline should flow in the order the events appear in the timestamp. No need
to worry about exact time values for this exercise.

## Sample Transcript

Feel free to use your favorite agent to generate some sample transcripts to
showcase your work.

## Deliverables

Please submit:

```
A GitHub repository containing your code
```

A (^) README.md with:
Setup and run instructions for both backend and frontend

```
Which LLM provider you used and how to configure the API key
Any design decisions or trade-offs you made
What you would improve or extend given more time
```

## Evaluation Criteria

We will evaluate:

```
Event extraction: Do the extracted events make clinical sense? Is BAML used
effectively to aid in this task?
API design: Clean, typed request/response shapes; appropriate error handling
Frontend quality: Timeline is readable, event types are visually differentiated,
async states are handled
Code clarity: Readable structure, sensible component and module
boundaries.
README Design thinking and decision making
```

