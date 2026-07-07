import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { AssistantKnowledgeSourcesCard } from './AssistantKnowledgeSourcesCard';

describe('AssistantKnowledgeSourcesCard', () => {
  it('renders grounded local sources', () => {
    render(
      <AssistantKnowledgeSourcesCard
        sources={[
          {
            path: 'docs/AI_ASSISTANT_SYSTEM_KNOWLEDGE.md',
            heading: 'Giving An Agent A Task',
            score: 0.93,
          },
        ]}
      />,
    );

    expect(screen.getByText('Knowledge Sources')).toBeInTheDocument();
    expect(screen.getByText('Giving An Agent A Task')).toBeInTheDocument();
    expect(screen.getByText('docs/AI_ASSISTANT_SYSTEM_KNOWLEDGE.md')).toBeInTheDocument();
  });

  it('renders an unavailable diagnostic', () => {
    render(<AssistantKnowledgeSourcesCard sources={[]} />);

    expect(screen.getByText('unavailable')).toBeInTheDocument();
    expect(screen.getByText(/knowledge doctor/i)).toBeInTheDocument();
  });
});
