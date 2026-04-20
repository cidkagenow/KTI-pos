import { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';
import { Button, Result } from 'antd';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  showDetails: boolean;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null, showDetails: false };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    this.setState({ errorInfo: info });
    console.error('ErrorBoundary caught:', error, info.componentStack);
  }

  handleReload = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    window.location.reload();
  };

  handleGoHome = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      const { error, errorInfo, showDetails } = this.state;
      return (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', background: '#f5f5f5' }}>
          <Result
            status="error"
            title="Algo salio mal"
            subTitle="Ocurrio un error inesperado. Intente recargar la pagina."
            extra={[
              <Button type="primary" key="reload" onClick={this.handleReload}>
                Recargar Pagina
              </Button>,
              <Button key="home" onClick={this.handleGoHome}>
                Ir al Inicio
              </Button>,
              <Button
                key="details"
                type="link"
                size="small"
                onClick={() => this.setState({ showDetails: !showDetails })}
              >
                {showDetails ? 'Ocultar detalles' : 'Ver detalles del error'}
              </Button>,
            ]}
          >
            {showDetails && (
              <div style={{
                textAlign: 'left',
                background: '#1a1a2e',
                color: '#e0e0e0',
                padding: 16,
                borderRadius: 8,
                fontSize: 12,
                fontFamily: 'monospace',
                maxHeight: 300,
                overflow: 'auto',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                marginTop: 16,
              }}>
                <div style={{ color: '#f87171', fontWeight: 'bold', marginBottom: 8 }}>
                  {error?.name}: {error?.message}
                </div>
                <div style={{ color: '#fbbf24', marginBottom: 8 }}>
                  {new Date().toLocaleString('es-PE')}
                </div>
                {error?.stack && (
                  <div style={{ opacity: 0.7, marginBottom: 12 }}>
                    {error.stack}
                  </div>
                )}
                {errorInfo?.componentStack && (
                  <div style={{ opacity: 0.5, borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: 8 }}>
                    Component stack:{errorInfo.componentStack}
                  </div>
                )}
              </div>
            )}
          </Result>
        </div>
      );
    }

    return this.props.children;
  }
}
