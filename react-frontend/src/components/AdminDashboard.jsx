import { useState, useEffect } from 'react'

function AdminDashboard({ onLogout }) {
    const [uploads, setUploads] = useState([])
    const [verifying, setVerifying] = useState({})

    useEffect(() => {
        fetchUploads()
    }, [])

    const fetchUploads = async () => {
        try {
            const response = await fetch('/admin')
            const html = await response.text()

            // Parse uploads from HTML
            const parser = new DOMParser()
            const doc = parser.parseFromString(html, 'text/html')

            const rows = doc.querySelectorAll('tbody tr')
            const uploadData = []

            rows.forEach((row, index) => {
                const cells = row.querySelectorAll('td')
                if (cells.length >= 7) {
                    const verifyBtn = row.querySelector('.verify-btn')
                    uploadData.push({
                        sno: cells[0].textContent.trim(),
                        filename: cells[1].textContent.trim(),
                        uploader: cells[2].textContent.trim(),
                        time: cells[3].textContent.trim(),
                        hash: verifyBtn ? verifyBtn.getAttribute('data-hash') : '',
                        verified: cells[5].textContent.trim()
                    })
                }
            })

            setUploads(uploadData)
        } catch (err) {
            console.error('Error fetching uploads:', err)
        }
    }

    const handleVerify = async (hash, sno) => {
        setVerifying(prev => ({ ...prev, [sno]: true }))

        try {
            const response = await fetch('/verify_report', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ hash })
            })
            const result = await response.json()

            setUploads(prev => prev.map(item =>
                item.sno === sno
                    ? { ...item, verified: result.status, onChain: result.on_chain }
                    : item
            ))
        } catch (err) {
            console.error('Verification error:', err)
        } finally {
            setVerifying(prev => ({ ...prev, [sno]: false }))
        }
    }

    const getStatusClass = (item) => {
        if (item.onChain === true) return 'verified'
        if (item.onChain === false) return 'not-verified'
        return 'pending'
    }

    return (
        <>
            <header>
                <h1>Admin Dashboard</h1>
                <button className="logout-btn" onClick={onLogout}>Logout</button>
            </header>

            <div className="container">
                <div className="card">
                    <h3>All Uploaded Reports</h3>
                    <table>
                        <thead>
                            <tr>
                                <th>S.No</th>
                                <th>File Name</th>
                                <th>Uploaded By</th>
                                <th>Time</th>
                                <th>Hash ID (Truncated)</th>
                                <th>Status</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {uploads.length > 0 ? (
                                uploads.map((item, index) => (
                                    <tr key={index}>
                                        <td>{item.sno}</td>
                                        <td>{item.filename}</td>
                                        <td>{item.uploader}</td>
                                        <td>{item.time}</td>
                                        <td title={item.hash}>{item.hash.substring(0, 15)}...</td>
                                        <td className={getStatusClass(item)}>{item.verified}</td>
                                        <td>
                                            <button
                                                className="verify-btn"
                                                onClick={() => handleVerify(item.hash, item.sno)}
                                                disabled={verifying[item.sno]}
                                            >
                                                {verifying[item.sno] && <span className="spinner"></span>}
                                                {verifying[item.sno] ? 'Checking...' : (item.onChain ? 'Verified' : 'Verify Local vs Chain')}
                                            </button>
                                            <a
                                                href={`/download/${item.filename}`}
                                                className="download-btn"
                                                style={{ textDecoration: 'none' }}
                                            >
                                                <button style={{ backgroundColor: '#27ae60', marginLeft: '5px' }}>
                                                    Download
                                                </button>
                                            </a>
                                        </td>
                                    </tr>
                                ))
                            ) : (
                                <tr>
                                    <td colSpan="7">No reports found.</td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </>
    )
}

export default AdminDashboard
