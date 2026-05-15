import Timeline from "@mui/lab/Timeline";
import TimelineConnector from "@mui/lab/TimelineConnector";
import TimelineContent from "@mui/lab/TimelineContent";
import TimelineDot from "@mui/lab/TimelineDot";
import TimelineItem from "@mui/lab/TimelineItem";
import TimelineOppositeContent from "@mui/lab/TimelineOppositeContent";
import TimelineSeparator from "@mui/lab/TimelineSeparator";
import * as Icons from "@mui/icons-material";
import { Typography } from "@mui/material";
import type { ComponentType } from "react";
import { EVENT_STYLES } from "../lib/eventStyling";
import type { Timeline as TimelineData, TimelineEvent } from "../api/types";
import { EventCard } from "./EventCard";

interface Props {
  timeline: TimelineData;
}

export function TimelineView({ timeline }: Props) {
  if (timeline.events.length === 0) return null;
  return (
    <Timeline position="right" sx={{ p: 0 }}>
      {timeline.events.map((event, idx) => (
        <Item
          key={`${event.order}-${event.type}`}
          event={event}
          isLast={idx === timeline.events.length - 1}
        />
      ))}
    </Timeline>
  );
}

function Item({ event, isLast }: { event: TimelineEvent; isLast: boolean }) {
  const style = EVENT_STYLES[event.type];
  const Icon = (Icons as Record<string, ComponentType>)[style.icon];
  return (
    <TimelineItem>
      <TimelineOppositeContent sx={{ flex: 0.15 }} color="text.secondary">
        <Typography variant="caption" display="block">
          #{event.order}
        </Typography>
        <Typography variant="caption" display="block">
          {style.label}
        </Typography>
      </TimelineOppositeContent>
      <TimelineSeparator>
        <TimelineDot color={style.color}>
          {Icon ? <Icon /> : null}
        </TimelineDot>
        {!isLast && <TimelineConnector />}
      </TimelineSeparator>
      <TimelineContent>
        <EventCard event={event} />
      </TimelineContent>
    </TimelineItem>
  );
}
