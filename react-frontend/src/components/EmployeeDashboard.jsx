import { useState, useEffect } from 'react'

function EmployeeDashboard({ user, onLogout }) {
    const [uploads, setUploads] = useState([])
    const [count, setCount] = useState(0)
    const [uploadStatus, setUploadStatus] = useState('')
    const [loading, setLoading] = useState(false)

    useEffect(() => {
        fetchUploads()
    }, [])

    const fetchUploads = async () => {
        try {
            const response = await fetch('/employee')
            const html = await response.text()

            // Parse uploads from HTML (simple approach)
            // In production, you'd have a proper API endpoint
            const parser = new DOMParser()
            const doc = parser.parseFromString(html, 'text/html')

            const rows = doc.querySelectorAll('tbody tr')
            const uploadData = []

            rows.forEach((row, index) => {
                const cells = row.querySelectorAll('td')
                if (cells.length >= 5) {
                    uploadData.push({
                        sno: cells[0].textContent.trim(),
                        filename: cells[1].textContent.trim(),
                        time: cells[2].textContent.trim(),
                        hash: cells[3].getAttribute('title') || cells[3].textContent.trim(),
                        verified: cells[4].textContent.trim()
                    })
                }
            })

            setUploads(uploadData)
            setCount(uploadData.length)
        } catch (err) {
            console.error('Error fetching uploads:', err)
        }
    }

    const handleUpload = async (e) => {
        e.preventDefault()
        const fileInput = document.getElementById('reportFile')

        if (!fileInput.files.length) {
            alert('Please select a file.')
            return
        }

        const formData = new FormData()
        formData.append('file', fileInput.files[0])

        setUploadStatus('Processing & Uploading to Blockchain...')
        setLoading(true)

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            })
            const result = await response.json()

            if (result.success) {
                setUploadStatus(`✓ Success!\nFile Hash: ${result.hash}`)
                setTimeout(() => {
                    setUploadStatus('')
                    fileInput.value = ''
                    fetchUploads()
                }, 3000)
            } else {
                setUploadStatus('Error: ' + result.error)
            }
        } catch (err) {
            setUploadStatus('Network Error.')
            console.error(err)
        } finally {
            setLoading(false)
        }
    }

    return (
        <>
            <header>
                <h1>Employee Dashboard</h1>
                <button className="logout-btn" onClick={onLogout}>Logout</button>
            </header>

            <div className="container">
                <div className="card stats">
                    <h3>Welcome, {user}</h3>
                    <p>Total Uploads: {count}</p>
                </div>

                <div className="card">
                    <h3>Upload New Malware Report</h3>
                    <form id="uploadForm" onSubmit={handleUpload}>
                        <div className="form-group">
                            <label>Select Report File (PDF/TXT)</label>
                            <input type="file" id="reportFile" required disabled={loading} />
                        </div>
                        <button type="submit" disabled={loading}>
                            {loading && <span className="spinner"></span>}
                            {loading ? 'Uploading...' : 'Secure Upload'}
                        </button>
                    </form>
                    {uploadStatus && (
                        <p style={{
                            marginTop: '10px',
                            fontWeight: 'bold',
                            whiteSpace: 'pre-line',
                            color: uploadStatus.includes('Success') ? 'green' : uploadStatus.includes('Error') ? 'red' : '#333'
                        }}>
                            {uploadStatus}
                        </p>
                    )}
                </div>

                <div className="card">
                    <h3>My Upload History</h3>
                    <table>
                        <thead>
                            <tr>
                                <th>S.No</th>
                                <th>File Name</th>
                                <th>Uploaded Time</th>
                                <th>Report Hash ID (Truncated)</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {uploads.length > 0 ? (
                                uploads.map((item, index) => (
                                    <tr key={index}>
                                        <td>{item.sno}</td>
                                        <td>{item.filename}</td>
                                        <td>{item.time}</td>
                                        <td title={item.hash}>{item.hash.substring(0, 20)}...</td>
                                        <td className="pending">{item.verified}</td>
                                    </tr>
                                ))
                            ) : (
                                <tr>
                                    <td colSpan="5">No files uploaded yet.</td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </>
    )
}

export default EmployeeDashboard
