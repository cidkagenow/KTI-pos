import { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';
import { Button, Result } from 'antd';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('ErrorBoundary caught:', error, info.componentStack);
  }

  handleReload = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  handleGoHome = () => {
    this.setState({ hasError: false, error: null });
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
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
            ]}
          />
        </div>
      );
    }

    return this.props.children;
  }
}
