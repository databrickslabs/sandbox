import React, { useState, useEffect, useCallback } from 'react'
import { Search, Plus, Edit3, Check, X, Users, Trash2 } from 'lucide-react'
import { roleColors } from './adminConstants'
import { normalizeRole, roleBadgeLabel } from '../../lib/roles'

function UsersList() {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [editingId, setEditingId] = useState(null)
  const [editForm, setEditForm] = useState({})
  const [search, setSearch] = useState('')
  const [showAdd, setShowAdd] = useState(false)
  const [addForm, setAddForm] = useState({ email: '', display_name: '', role: 'analyst', department: '' })
  const [adding, setAdding] = useState(false)
  const [addError, setAddError] = useState('')

  // ── SCIM search state ──────────────────────────────────────────────────────
  const [scimQuery, setScimQuery] = useState('')
  const [scimResults, setScimResults] = useState([])
  const [scimLoading, setScimLoading] = useState(false)
  const scimTimer = React.useRef(null)

  const loadUsers = useCallback(() => {
    fetch('/api/portal/admin/users')
      .then(r => r.json())
      .then(rows => { if (Array.isArray(rows)) setUsers(rows) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { loadUsers() }, [loadUsers])

  // Debounced SCIM lookup
  const handleScimInput = (val) => {
    setScimQuery(val)
    setAddForm(f => ({ ...f, email: val, display_name: f.display_name }))
    clearTimeout(scimTimer.current)
    if (val.length < 2) { setScimResults([]); return }
    setScimLoading(true)
    scimTimer.current = setTimeout(() => {
      fetch(`/api/portal/admin/scim-search?q=${encodeURIComponent(val)}`)
        .then(r => r.json())
        .then(rows => setScimResults(Array.isArray(rows) ? rows : []))
        .catch(() => setScimResults([]))
        .finally(() => setScimLoading(false))
    }, 300)
  }

  const selectScimUser = (u) => {
    setAddForm(f => ({ ...f, email: u.email, display_name: u.display_name }))
    setScimQuery(u.display_name)
    setScimResults([])
  }

  const startEdit = (user) => {
    setEditingId(user.user_id)
    setEditForm({ role: normalizeRole(user.role), department: user.department || '' })
  }

  const saveEdit = async (userId) => {
    try {
      await fetch(`/api/portal/admin/users/${userId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editForm)
      })
      setEditingId(null)
      loadUsers()
    } catch (e) { console.error(e) }
  }

  const handleAddUser = async () => {
    if (!addForm.email.trim()) { setAddError('Email is required'); return }
    setAdding(true); setAddError('')
    try {
      const r = await fetch('/api/portal/admin/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(addForm)
      })
      if (!r.ok) { const d = await r.json(); setAddError(d.error || 'Failed to add user'); return }
      setShowAdd(false)
      setAddForm({ email: '', display_name: '', role: 'analyst', department: '' })
      setScimQuery('')
      setScimResults([])
      loadUsers()
    } catch (e) { setAddError(e.message) }
    finally { setAdding(false) }
  }

  const filtered = users.filter(u =>
    !search || u.display_name?.toLowerCase().includes(search.toLowerCase()) || u.email?.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input type="text" placeholder="Search users" value={search} onChange={e => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
        <button
          onClick={() => { setShowAdd(v => !v); setAddError(''); setScimQuery(''); setScimResults([]) }}
          className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium text-white"
          style={{ backgroundColor: '#003865' }}
        >
          <Plus className="h-4 w-4" /> Add User
        </button>
      </div>

      {showAdd && (
        <div className="mb-4 p-4 bg-blue-50/60 border border-blue-100 rounded-xl">
          <p className="text-sm font-semibold text-gray-800 mb-1">Add / update a user</p>
          <p className="text-xs text-gray-500 mb-3">Search by name or email — picks from your Databricks workspace users</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">

            {/* SCIM search input */}
            <div className="relative sm:col-span-2">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                placeholder="Search workspace users (name or email) *"
                value={scimQuery}
                onChange={e => handleScimInput(e.target.value)}
                autoComplete="off"
                className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              {(scimLoading || scimResults.length > 0) && (
                <div className="absolute top-full left-0 right-0 bg-white border border-gray-200 rounded-xl shadow-lg z-20 mt-1 overflow-hidden">
                  {scimLoading && (
                    <div className="px-4 py-3 text-xs text-gray-400">Searching workspace users...</div>
                  )}
                  {!scimLoading && scimResults.map((u, i) => (
                    <button
                      key={i}
                      onMouseDown={() => selectScimUser(u)}
                      className="w-full text-left px-4 py-2.5 hover:bg-blue-50 flex items-center gap-3 border-b border-gray-50 last:border-0"
                    >
                      <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white text-xs font-bold shrink-0">
                        {(u.display_name || u.email).split(' ').map(w => w[0]).join('').substring(0, 2).toUpperCase()}
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-900">{u.display_name}</p>
                        <p className="text-xs text-gray-400">{u.email}</p>
                      </div>
                    </button>
                  ))}
                  {!scimLoading && scimResults.length === 0 && scimQuery.length >= 2 && (
                    <div className="px-4 py-3 text-xs text-gray-500">
                      No workspace users found — you can still enter an email manually below
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Manual email fallback (pre-filled from SCIM selection) */}
            <input
              placeholder="Email *"
              value={addForm.email}
              onChange={e => setAddForm(f => ({ ...f, email: e.target.value }))}
              className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <input
              placeholder="Display name"
              value={addForm.display_name}
              onChange={e => setAddForm(f => ({ ...f, display_name: e.target.value }))}
              className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <select
              value={addForm.role}
              onChange={e => setAddForm(f => ({ ...f, role: e.target.value }))}
              className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="analyst">Analyst</option>
              <option value="admin">Admin / Data Steward</option>
            </select>
            <input
              placeholder="Department"
              value={addForm.department}
              onChange={e => setAddForm(f => ({ ...f, department: e.target.value }))}
              className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          {addError && <p className="text-xs text-red-500 mb-2">{addError}</p>}
          <div className="flex gap-2">
            <button
              onClick={handleAddUser}
              disabled={adding}
              className="px-4 py-2 rounded-lg text-sm font-medium text-white disabled:opacity-50"
              style={{ backgroundColor: '#003865' }}
            >
              {adding ? 'Saving...' : 'Save User'}
            </button>
            <button onClick={() => setShowAdd(false)} className="px-4 py-2 rounded-lg text-sm font-medium border border-gray-200 text-gray-600 hover:bg-gray-50">
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="text-left py-3 px-4 font-medium text-gray-500 text-xs uppercase tracking-wide">Name</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500 text-xs uppercase tracking-wide">Email</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500 text-xs uppercase tracking-wide">Role</th>
                <th className="text-left py-3 px-4 font-medium text-gray-500 text-xs uppercase tracking-wide">Department</th>
                <th className="text-center py-3 px-4 font-medium text-gray-500 text-xs uppercase tracking-wide w-20">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr><td colSpan={5} className="py-12 text-center text-gray-400 text-sm">Loading users...</td></tr>
              )}
              {!loading && filtered.length === 0 && (
                <tr><td colSpan={5} className="py-12 text-center text-gray-400 text-sm">No users found.</td></tr>
              )}
              {filtered.map(user => {
                const isEditing = editingId === user.user_id
                return (
                  <tr key={user.user_id} className={`border-b border-gray-100 ${isEditing ? 'bg-blue-50/50' : 'hover:bg-gray-50'} transition-colors`}>
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <div className="w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold text-white shrink-0"
                          style={{ backgroundColor: normalizeRole(user.role) === 'admin' ? '#8B5CF6' : '#3B82F6' }}>
                          {(user.display_name || user.email).split(' ').map(w => w[0]).join('').substring(0, 2).toUpperCase()}
                        </div>
                        <span className="font-medium text-gray-900 text-xs">{user.display_name || user.email}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-xs text-gray-500">{user.email}</td>
                    <td className="py-3 px-4">
                      {isEditing ? (
                        <select value={editForm.role} onChange={e => setEditForm({ ...editForm, role: e.target.value })}
                          className="px-2 py-1 border border-blue-200 rounded text-xs focus:outline-none">
                          <option value="analyst">Analyst</option>
                          <option value="admin">Admin / Data Steward</option>
                        </select>
                      ) : (
                        <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${roleColors[normalizeRole(user.role)] || 'bg-gray-100 text-gray-700'}`}>
                          {roleBadgeLabel(user.role)}
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      {isEditing ? (
                        <input value={editForm.department} onChange={e => setEditForm({ ...editForm, department: e.target.value })}
                          className="w-full px-2 py-1 border border-blue-200 rounded text-xs focus:outline-none focus:ring-1 focus:ring-blue-400" />
                      ) : (
                        <span className="text-xs text-gray-600">{user.department || '-'}</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-center">
                      {isEditing ? (
                        <div className="flex gap-1 justify-center">
                          <button onClick={() => saveEdit(user.user_id)} className="p-1 rounded bg-emerald-100 text-emerald-700 hover:bg-emerald-200"><Check className="h-3.5 w-3.5" /></button>
                          <button onClick={() => setEditingId(null)} className="p-1 rounded bg-gray-100 text-gray-500 hover:bg-gray-200"><X className="h-3.5 w-3.5" /></button>
                        </div>
                      ) : (
                        <button onClick={() => startEdit(user)} className="p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-700">
                          <Edit3 className="h-3.5 w-3.5" />
                        </button>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

// ─── Groups Panel ─────────────────────────────────────────────────────────────
function GroupsList() {
  const [groups, setGroups] = useState([])
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [addForm, setAddForm] = useState({ group_name: '', scim_id: '', role: 'analyst', department: '' })
  const [adding, setAdding] = useState(false)
  const [scimQuery, setScimQuery] = useState('')
  const [scimResults, setScimResults] = useState([])
  const [scimLoading, setScimLoading] = useState(false)
  const scimTimer = React.useRef(null)

  const loadGroups = useCallback(() => {
    fetch('/api/portal/admin/groups')
      .then(r => r.json())
      .then(rows => { if (Array.isArray(rows)) setGroups(rows) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { loadGroups() }, [loadGroups])

  const handleScimGroupInput = (val) => {
    setScimQuery(val)
    setAddForm(f => ({ ...f, group_name: val, scim_id: '' }))
    clearTimeout(scimTimer.current)
    if (val.length < 1) { setScimResults([]); return }
    setScimLoading(true)
    scimTimer.current = setTimeout(() => {
      fetch(`/api/portal/admin/scim-groups-search?q=${encodeURIComponent(val)}`)
        .then(r => r.json())
        .then(rows => setScimResults(Array.isArray(rows) ? rows : []))
        .catch(() => setScimResults([]))
        .finally(() => setScimLoading(false))
    }, 300)
  }

  const selectGroup = (g) => {
    setAddForm(f => ({ ...f, group_name: g.group_name, scim_id: g.scim_id }))
    setScimQuery(g.group_name)
    setScimResults([])
  }

  const handleAddGroup = async () => {
    if (!addForm.group_name.trim()) return
    setAdding(true)
    try {
      const r = await fetch('/api/portal/admin/groups', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(addForm)
      })
      if (r.ok) {
        setShowAdd(false)
        setAddForm({ group_name: '', scim_id: '', role: 'analyst', department: '' })
        setScimQuery(''); setScimResults([])
        loadGroups()
      }
    } catch (_) {}
    finally { setAdding(false) }
  }

  const deleteGroup = async (id) => {
    if (!window.confirm('Remove this group?')) return
    await fetch(`/api/portal/admin/groups/${id}`, { method: 'DELETE' })
    loadGroups()
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <p className="text-xs text-gray-500">Groups assigned a role here automatically grant that role to members on first login.</p>
        <button
          onClick={() => { setShowAdd(v => !v); setScimQuery(''); setScimResults([]) }}
          className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium text-white shrink-0"
          style={{ backgroundColor: '#003865' }}
        >
          <Plus className="h-4 w-4" /> Add Group
        </button>
      </div>

      {showAdd && (
        <div className="mb-4 p-4 bg-violet-50/60 border border-violet-100 rounded-xl">
          <p className="text-sm font-semibold text-gray-800 mb-1">Add a workspace group</p>
          <p className="text-xs text-gray-500 mb-3">Search your Databricks/Entra ID groups by name</p>

          {/* SCIM group search */}
          <div className="relative mb-3">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              placeholder="Search workspace groups *"
              value={scimQuery}
              onChange={e => handleScimGroupInput(e.target.value)}
              autoComplete="off"
              className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-violet-400"
            />
            {(scimLoading || scimResults.length > 0) && (
              <div className="absolute top-full left-0 right-0 bg-white border border-gray-200 rounded-xl shadow-lg z-20 mt-1 overflow-hidden">
                {scimLoading && <div className="px-4 py-3 text-xs text-gray-400">Searching groups...</div>}
                {!scimLoading && scimResults.map((g, i) => (
                  <button key={i} onMouseDown={() => selectGroup(g)}
                    className="w-full text-left px-4 py-2.5 hover:bg-violet-50 flex items-center gap-3 border-b border-gray-50 last:border-0">
                    <div className="w-8 h-8 rounded-lg bg-violet-100 flex items-center justify-center shrink-0">
                      <Users className="h-4 w-4 text-violet-600" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-900">{g.group_name}</p>
                      {g.member_count > 0 && <p className="text-xs text-gray-400">{g.member_count} member{g.member_count !== 1 ? 's' : ''}</p>}
                    </div>
                  </button>
                ))}
                {!scimLoading && scimResults.length === 0 && scimQuery.length >= 1 && (
                  <div className="px-4 py-3 text-xs text-gray-500">No groups found — you can still type a group name manually</div>
                )}
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3 mb-3">
            <select value={addForm.role} onChange={e => setAddForm(f => ({ ...f, role: e.target.value }))}
              className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-400">
              <option value="analyst">Analyst</option>
              <option value="admin">Admin / Data Steward</option>
            </select>
            <input placeholder="Department (optional)" value={addForm.department}
              onChange={e => setAddForm(f => ({ ...f, department: e.target.value }))}
              className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-400" />
          </div>
          <div className="flex gap-2">
            <button onClick={handleAddGroup} disabled={adding || !addForm.group_name.trim()}
              className="px-4 py-2 rounded-lg text-sm font-medium text-white disabled:opacity-50"
              style={{ backgroundColor: '#003865' }}>
              {adding ? 'Saving...' : 'Save Group'}
            </button>
            <button onClick={() => setShowAdd(false)} className="px-4 py-2 rounded-lg text-sm font-medium border border-gray-200 text-gray-600 hover:bg-gray-50">Cancel</button>
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50">
              <th className="text-left py-3 px-4 font-medium text-gray-500 text-xs uppercase tracking-wide">Group Name</th>
              <th className="text-left py-3 px-4 font-medium text-gray-500 text-xs uppercase tracking-wide">Role Assigned</th>
              <th className="text-left py-3 px-4 font-medium text-gray-500 text-xs uppercase tracking-wide">Department</th>
              <th className="text-center py-3 px-4 font-medium text-gray-500 text-xs uppercase tracking-wide w-16">Remove</th>
            </tr>
          </thead>
          <tbody>
            {loading && <tr><td colSpan={4} className="py-12 text-center text-gray-400 text-sm">Loading groups...</td></tr>}
            {!loading && groups.length === 0 && (
              <tr><td colSpan={4} className="py-10 text-center text-gray-400 text-sm">
                No groups configured. Add a group to automatically assign roles to its members.
              </td></tr>
            )}
            {groups.map(g => (
              <tr key={g.group_id} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="py-3 px-4">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-lg bg-violet-100 flex items-center justify-center shrink-0">
                      <Users className="h-3.5 w-3.5 text-violet-600" />
                    </div>
                    <span className="font-medium text-gray-900 text-xs">{g.group_name}</span>
                  </div>
                </td>
                <td className="py-3 px-4">
                  <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${roleColors[normalizeRole(g.role)] || 'bg-gray-100 text-gray-700'}`}>
                    {roleBadgeLabel(g.role)}
                  </span>
                </td>
                <td className="py-3 px-4 text-xs text-gray-500">{g.department || '-'}</td>
                <td className="py-3 px-4 text-center">
                  <button onClick={() => deleteGroup(g.group_id)} className="p-1 rounded bg-red-50 text-red-400 hover:bg-red-100 hover:text-red-600">
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ─── Users Tab (Steward Only) ──────────────────────────────────────────────────
export function AdminUsersTab() {
  const [activeView, setActiveView] = useState('users') // 'users' | 'groups'

  return (
    <div>
      {/* Users / Groups toggle */}
      <div className="flex gap-1 mb-4 bg-gray-100 rounded-lg p-1 w-fit">
        {[{ id: 'users', label: 'Users' }, { id: 'groups', label: 'Groups' }].map(v => (
          <button key={v.id} onClick={() => setActiveView(v.id)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
              activeView === v.id ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            }`}>
            {v.label}
          </button>
        ))}
      </div>
      {activeView === 'users' ? <UsersList /> : <GroupsList />}
    </div>
  )
}
