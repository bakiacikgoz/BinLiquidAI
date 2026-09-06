import { Workflow } from 'lucide-react';
import { productText } from '../ui/productCopy';

export function CollectionPage() {
  const t = productText();
  return <main className="collection-page">
    <header><span className="collection-icon"><Workflow size={21} /></span><p>{t('Not available yet')}</p><h1>{t('Scheduled tasks')}</h1><span>{t('Scheduled tasks are not supported by this desktop version.')}</span></header>
    <section className="collection-list"><p className="collection-empty">{t('You can start a task manually. No schedule has been created.')}</p><a className="collection-manual-task" href="#/">{t('New task')}</a></section>
  </main>;
}
