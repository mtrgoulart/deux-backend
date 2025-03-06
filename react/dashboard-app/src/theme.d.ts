import '@mui/material/styles';

declare module '@mui/material/styles' {
  interface Theme {
    vars?: {
      palette: {
        text: {
          secondary: string;
        };
        primary: {
          main: string;
        };
        success: {
          main: string;
        };
        // Adicione outras propriedades conforme necessário
      };
    };
  }
  interface ThemeOptions {
    vars?: {
      palette?: {
        text?: {
          secondary?: string;
        };
        primary?: {
          main?: string;
        };
        success?: {
          main?: string;
        };
      };
    };
  }
}
