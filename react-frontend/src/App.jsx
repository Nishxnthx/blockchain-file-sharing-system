import { useState, useEffect } from 'react'
import Login from './components/Login'
import EmployeeDashboard from './components/EmployeeDashboard'
import AdminDashboard from './components/AdminDashboard'

function App() {
    const [user, setUser] = useState(null)
    const [role, setRole] = useState(null)

    useEffect(() => {
        // Check if user is already logged in (from session)
        const storedUser = sessionStorage.getItem('user')
        const storedRole = sessionStorage.getItem('role')
        if (storedUser && storedRole) {
            setUser(storedUser)
            setRole(storedRole)
        }
    }, [])

    const handleLogin = (username, userRole) => {
        setUser(username)
        setRole(userRole)
        sessionStorage.setItem('user', username)
        sessionStorage.setItem('role', userRole)
    }

    const handleLogout = async () => {
        await fetch('/logout')
        setUser(null)
        setRole(null)
        sessionStorage.removeItem('user')
        sessionStorage.removeItem('role')
    }

    if (!user) {
        return <Login onLogin={handleLogin} />
    }

    if (role === 'employee') {
        return <EmployeeDashboard user={user} onLogout={handleLogout} />
    }

    if (role === 'admin') {
        return <AdminDashboard onLogout={handleLogout} />
    }

    return null
}

export default App
