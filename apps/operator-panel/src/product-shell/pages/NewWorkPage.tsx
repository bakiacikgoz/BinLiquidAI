import { useNavigate } from 'react-router-dom';

import { Composer } from '../composer/Composer';
import { useProductShellStore } from '../state/productShellStore';

export function NewWorkPage() {
  const createTask = useProductShellStore((state) => state.createTask);
  const navigate = useNavigate();
  const start = (message: string) => { const task = createTask(message); navigate(`/task/${task.id}`); };
  return <section className="ps-new-work"><div><p className="ps-eyebrow">GOVERNED OPERATOR WORKSPACE</p><h1>What should ImperaOS help you accomplish?</h1><p>Plan a task, inspect the evidence, and route changes through the existing approval and artifact controls.</p></div><Composer onSend={start} /></section>;
}
