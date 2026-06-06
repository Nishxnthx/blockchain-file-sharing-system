import { useState } from 'react'

function Login({ onLogin }) {
    const [username, setUsername] = useState('')
    const [password, setPassword] = useState('')
    const [role, setRole] = useState('employee')
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)

    const handleSubmit = async (e) => {
        e.preventDefault()
        setError('')
        setLoading(true)

        try {
            const formData = new FormData()
            formData.append('username', username)
            formData.append('password', password)
            formData.append('role', role)

            const response = await fetch('/login', {
                method: 'POST',
                body: formData
            })

            if (response.redirected) {
                // Login successful
                onLogin(username, role)
            } else {
                const text = await response.text()
                if (text.includes('Invalid credentials')) {
                    setError('Invalid credentials')
                } else {
                    setError('Login failed')
                }
            }
        } catch (err) {
            setError('Network error. Please try again.')
            console.error(err)
        } finally {
            setLoading(false)
        }
    }

    return (
        <>
            <header>
                <h1>Blockchain-Based Malware Reporting System</h1>
            </header>

            <div className="login-wrapper">
                <h2>Login</h2>
                {error && <div className="alert">{error}</div>}
                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label htmlFor="username">Username</label>
                        <input
                            type="text"
                            id="username"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            placeholder="e.g. emp1 or admin"
                            required
                        />
                    </div>
                    <div className="form-group">
                        <label htmlFor="password">Password</label>
                        <input
                            type="password"
                            id="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="e.g. 123 or admin"
                            required
                        />
                    </div>
                    <div className="form-group">
                        <label htmlFor="role">Role</label>
                        <select
                            id="role"
                            value={role}
                            onChange={(e) => setRole(e.target.value)}
                        >
                            <option value="employee">Employee</option>
                            <option value="admin">Admin</option>
                        </select>
                    </div>
                    <button type="submit" disabled={loading}>
                        {loading && <span className="spinner"></span>}
                        {loading ? 'Signing In...' : 'Sign In'}
                    </button>
                </form>
                <p style={{ marginTop: '10px', fontSize: '0.9em', color: '#666' }}>
                    Demo Creds:<br />
                    Employee: emp1 / 123<br />
                    Admin: admin / admin
                </p>
            </div>
        </>
    )
}

export default Login
