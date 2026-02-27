import React from 'react'
import { BrowserRouter as Router } from 'react-router-dom'
import { App as AntdApp } from 'antd'
import ErrorBoundary from './components/ErrorBoundary'
import AppRouter from './components/AppRouter'
// import './utils/configTest' // 导入配置测试（仅在开发环境生效）

function App() {
  return (
    <ErrorBoundary>
      <AntdApp>
        <Router>
          <AppRouter />
        </Router>
      </AntdApp>
    </ErrorBoundary>
  )
}

export default App