import { useLayoutEffect } from 'react';
import { getCurrentWindow } from '@tauri-apps/api/window';

import tokens from './ui-lab/tokens.css?inline';
import globals from './ui-lab/globals.css?inline';
import surfaces from './ui-lab/surfaces.css?inline';
import adapters from './shell.css?inline';

const runtimeGlobals = globals.replace(/^@import\s+['"].+?['"];\s*$/gm, '');
const uiLabTheme = `${tokens}\n${runtimeGlobals}\n${surfaces}`;

export function ProductTheme({ theme }: { theme: 'dark' | 'light' }) {
  useLayoutEffect(() => {
    const previousTheme = document.documentElement.dataset.theme;
    const nativeMac = '__TAURI_INTERNALS__' in window && /Mac/.test(navigator.platform);
    document.documentElement.classList.toggle('product-native-mac', nativeMac);
    if (nativeMac) {
      void getCurrentWindow().setTheme(theme).catch((error: unknown) => {
        console.warn('Native window theme could not be synchronized', error);
      });
    }
    document.documentElement.dataset.theme = theme;
    return () => {
      document.documentElement.classList.remove('product-native-mac');
      if (previousTheme) {
        document.documentElement.dataset.theme = previousTheme;
      } else {
        delete document.documentElement.dataset.theme;
      }
    };
  }, [theme]);

  return <>
    <style data-ui-lab-theme>{uiLabTheme}</style>
    <style data-product-shell-adapters>{adapters}</style>
  </>;
}
