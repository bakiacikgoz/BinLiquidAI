import './styles/shell.css';
import { BrowserApprovalInbox } from './browser/BrowserApprovalInbox';
import { ProductRouter } from './router/ProductRouter';

export function ProductShellApp() { return <><ProductRouter /><BrowserApprovalInbox /></>; }
