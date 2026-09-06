import { desktopConnected, productText } from './productCopy';

export function RuntimeNotice() {
  if (desktopConnected()) return null;
  const t = productText();
  const preview = import.meta.env.DEV || import.meta.env.MODE === 'test'
    || ['1', 'true'].includes(import.meta.env.VITE_OPERATOR_PANEL_PREVIEW);
  return <p className="product-runtime-notice" role="status">{t(preview
    ? 'Preview · Sample data may appear here. Use the desktop app for live workspace data and actions.'
    : 'Browser view · Open the desktop app to connect to your workspace.')}</p>;
}
