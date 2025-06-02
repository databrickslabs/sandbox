import sqlite3
import threading
import json
from fastapi import HTTPException
from datetime import datetime
import logging
from models import MessageResponse, ChatHistoryItem, ChatHistoryResponse

logger = logging.getLogger(__name__)

class ChatDatabase:
    def __init__(self, db_file='chat_history.db'):
        self.db_file = db_file
        self.db_lock = threading.Lock()
        self.connection_pool = {}
        self.first_message_cache = {}
        self.init_db()
    
    def get_connection(self):
        """Get a database connection from the pool or create a new one"""
        thread_id = threading.get_ident()
        if thread_id not in self.connection_pool:
            conn = sqlite3.connect(self.db_file)
            conn.row_factory = sqlite3.Row
            self.connection_pool[thread_id] = conn
        return self.connection_pool[thread_id]
    
    def close_connection(self):
        """Close the database connection for the current thread"""
        thread_id = threading.get_ident()
        if thread_id in self.connection_pool:
            self.connection_pool[thread_id].close()
            del self.connection_pool[thread_id]
    
    def init_db(self):
        """Initialize the database with required tables and indexes"""
        with self.db_lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            try:
                # Enable foreign key constraints
                cursor.execute('PRAGMA foreign_keys = ON')
                
                # Create sessions table with user information
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    user_email TEXT,
                    first_query TEXT,
                    timestamp TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                ''')
                
                # Create messages table
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    role TEXT NOT NULL,
                    model TEXT,
                    timestamp TEXT NOT NULL,
                    sources TEXT,
                    metrics TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                )
                ''')
                
                # Create ratings table
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS message_ratings (
                    message_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    rating TEXT CHECK(rating IN ('up', 'down')),
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (message_id, user_id),
                    FOREIGN KEY (message_id) REFERENCES messages(message_id) ON DELETE CASCADE,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
                )
                ''')
                
                # Create indexes for better query performance
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_timestamp ON sessions(timestamp)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_ratings_message_id ON message_ratings(message_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_ratings_user_id ON message_ratings(user_id)')
                
                conn.commit()
            except sqlite3.Error as e:
                logger.error(f"Error initializing database: {str(e)}")
                raise
            finally:
                cursor.close()
    
    def save_message_to_session(self, session_id: str, user_id: str, message: MessageResponse, user_info: dict = None, is_first_message: bool = False):
        """Save a message to a chat session, creating the session if it doesn't exist"""
        with self.db_lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            try:
                conn.execute('BEGIN TRANSACTION')
                
                logger.info(f"Saving message: session_id={session_id}, user_id={user_id}, message_id={message.message_id}")
                
                # Check if session exists
                cursor.execute('SELECT session_id FROM sessions WHERE session_id = ? and user_id = ?', (session_id, user_id))
                if not cursor.fetchone():
                    logger.info(f"Creating new session: session_id={session_id}, user_id={user_id}")
                    # Create new session with user info
                    cursor.execute('''
                    INSERT INTO sessions (session_id, user_id, user_email, first_query, timestamp, is_active)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        session_id,
                        user_id,  # Use the provided user_id directly
                        user_info.get('email') if user_info else None,
                        message.content if is_first_message else "",
                        message.timestamp.isoformat(),
                        1
                    ))
                
                # Save message with user_id
                cursor.execute('''
                INSERT INTO messages (
                    message_id, session_id, user_id, content, role, model, 
                    timestamp, sources, metrics
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    message.message_id,
                    session_id,
                    user_id,  # Use the provided user_id directly
                    message.content,
                    message.role,
                    message.model,
                    message.timestamp.isoformat(),
                    json.dumps(message.sources) if message.sources else None,
                    json.dumps(message.metrics) if message.metrics else None
                ))
                
                # Update cache after saving message
                self.first_message_cache[session_id] = False
                
                conn.commit()
            except sqlite3.Error as e:
                conn.rollback()
                logger.error(f"Error saving message to session: {str(e)}")
                raise
            finally:
                cursor.close()
    
    def update_message(self, session_id: str, user_id: str, message: MessageResponse):
        """Update an existing message in the database"""
        with self.db_lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            try:
                conn.execute('BEGIN TRANSACTION')
                
                cursor.execute('''
                UPDATE messages 
                SET content = ?, 
                    role = ?, 
                    model = ?, 
                    timestamp = ?, 
                    sources = ?, 
                    metrics = ?
                WHERE message_id = ? AND session_id = ? AND user_id = ?
                ''', (
                    message.content,
                    message.role,
                    message.model,
                    message.timestamp.isoformat(),
                    json.dumps(message.sources) if message.sources else None,
                    json.dumps(message.metrics) if message.metrics else None,
                    message.message_id,
                    session_id,
                    user_id
                ))
                
                if cursor.rowcount == 0:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Message {message.message_id} not found in session {session_id}"
                    )
                
                conn.commit()
            except sqlite3.Error as e:
                conn.rollback()
                logger.error(f"Error updating message: {str(e)}")
                raise
            finally:
                cursor.close()
    
    def get_chat_history(self, user_id: str = None) -> ChatHistoryResponse:
        """Retrieve chat sessions with their messages for a specific user"""
        with self.db_lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            try:
                if user_id:
                    cursor.execute('''
                    SELECT s.session_id, s.first_query, s.timestamp, s.is_active,
                           m.message_id, m.content, m.role, m.model, m.timestamp as message_timestamp,
                           m.sources, m.metrics, m.created_at
                    FROM sessions s
                    LEFT JOIN messages m ON s.session_id = m.session_id and m.user_id = s.user_id
                    WHERE s.user_id = ?
                    ORDER BY s.created_at DESC, m.created_at ASC
                    ''', (user_id,))
                else:
                    cursor.execute('''
                    SELECT s.session_id, s.first_query, s.timestamp, s.is_active,
                           m.message_id, m.content, m.role, m.model, m.timestamp as message_timestamp,
                           m.sources, m.metrics, m.created_at
                    FROM sessions s
                    LEFT JOIN messages m ON s.session_id = m.session_id and m.user_id = s.user_id
                    ORDER BY s.created_at DESC, m.created_at ASC
                    ''')
                
                sessions = {}
                for row in cursor.fetchall():
                    session_id = row['session_id']
                    if session_id not in sessions:
                        sessions[session_id] = ChatHistoryItem(
                            sessionId=session_id,
                            firstQuery=row['first_query'],
                            messages=[],
                            timestamp=datetime.fromisoformat(row['timestamp']),
                            isActive=bool(row['is_active'])
                        )
                    
                    if row['message_id']:  # message_id exists
                        sessions[session_id].messages.append(MessageResponse(
                            message_id=row['message_id'],
                            content=row['content'],
                            role=row['role'],
                            model=row['model'],
                            timestamp=datetime.fromisoformat(row['message_timestamp']),
                            created_at=datetime.fromisoformat(row['created_at']),
                            sources=json.loads(row['sources']) if row['sources'] else None,
                            metrics=json.loads(row['metrics']) if row['metrics'] else None
                        ))
                
                # Sort messages by created_at for each session
                for session in sessions.values():
                    session.messages.sort(key=lambda x: x.created_at)
                
                return ChatHistoryResponse(sessions=list(sessions.values()))
            except sqlite3.Error as e:
                logger.error(f"Error getting chat history: {str(e)}")
                raise
            finally:
                cursor.close()
    
    def get_chat(self, session_id: str, user_id: str = None) -> ChatHistoryItem:
        """Retrieve a specific chat session"""
        with self.db_lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            try:
                logger.info(f"Getting chat for session_id: {session_id}, user_id: {user_id}")
                
                # Get session info with user check
                if user_id:
                    cursor.execute('''
                    SELECT first_query, timestamp, is_active, created_at
                    FROM sessions
                    WHERE session_id = ? AND user_id = ?
                    ''', (session_id, user_id))
                else:
                    cursor.execute('''
                    SELECT first_query, timestamp, is_active, created_at
                    FROM sessions
                    WHERE session_id = ?
                    ''', (session_id,))
                
                session_data = cursor.fetchone()
                if not session_data:
                    logger.error(f"Session not found: session_id={session_id}, user_id={user_id}")
                    raise HTTPException(status_code=404, detail="Chat not found")
                
                # Get messages ordered by created_at
                cursor.execute('''
                SELECT message_id, content, role, model, timestamp, sources, metrics, user_id, created_at
                FROM messages
                WHERE session_id = ? and user_id = ?
                ORDER BY created_at ASC
                ''', (session_id, user_id))
                
                messages = []
                for row in cursor.fetchall():
                    logger.info(f"Found message: message_id={row['message_id']}, user_id={row['user_id']}")
                    messages.append(MessageResponse(
                        message_id=row['message_id'],
                        content=row['content'],
                        role=row['role'],
                        model=row['model'],
                        timestamp=datetime.fromisoformat(row['timestamp']),
                        created_at=datetime.fromisoformat(row['created_at']),
                        sources=json.loads(row['sources']) if row['sources'] else None,
                        metrics=json.loads(row['metrics']) if row['metrics'] else None
                    ))
                
                return ChatHistoryItem(
                    sessionId=session_id,
                    firstQuery=session_data['first_query'],
                    messages=messages,
                    timestamp=datetime.fromisoformat(session_data['timestamp']),
                    created_at=datetime.fromisoformat(session_data['created_at']),
                    isActive=bool(session_data['is_active'])
                )
            except sqlite3.Error as e:
                logger.error(f"Error getting chat: {str(e)}")
                raise
            finally:
                cursor.close()
    
    def clear_session(self, session_id: str, user_id: str):
        """Clear a session and its messages"""
        with self.db_lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            try:
                conn.execute('BEGIN TRANSACTION')
                
                # Delete messages
                cursor.execute('DELETE FROM messages WHERE session_id = ? and user_id = ?', (session_id, user_id))
                # Delete session
                cursor.execute('DELETE FROM sessions WHERE session_id = ? and user_id = ?', (session_id, user_id))
                # Clear cache
                if session_id in self.first_message_cache:
                    del self.first_message_cache[session_id]
                
                conn.commit()
            except sqlite3.Error as e:
                conn.rollback()
                logger.error(f"Error clearing session: {str(e)}")
                raise
            finally:
                cursor.close()
    
    def is_first_message(self, session_id: str, user_id: str) -> bool:
        """Check if this is the first message in a session"""
        # Check cache first
        if session_id in self.first_message_cache:
            return self.first_message_cache[session_id]
            
        with self.db_lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                SELECT COUNT(*) FROM messages 
                WHERE session_id = ? and user_id = ?
                ''', (session_id, user_id))
                
                count = cursor.fetchone()[0]
                is_first = count == 0
                
                # Update cache
                self.first_message_cache[session_id] = is_first
                return is_first
            except sqlite3.Error as e:
                logger.error(f"Error checking first message: {str(e)}")
                raise
            finally:
                cursor.close()

    def update_message_rating(self, message_id: str, user_id: str, rating: str | None) -> bool:
        with self.db_lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            try:
                conn.execute('BEGIN TRANSACTION')
                
                # First verify the message exists and belongs to the user
                cursor.execute('''
                SELECT message_id, session_id FROM messages 
                WHERE message_id = ? AND user_id = ?
                ''', (message_id, user_id))
                
                result = cursor.fetchone()
                if not result:
                    logger.error(f"Message {message_id} not found for user {user_id}")
                    conn.rollback()
                    return False
                
                session_id = result['session_id']
                
                if rating is None:
                    # Remove the rating
                    cursor.execute('''
                    DELETE FROM message_ratings 
                    WHERE message_id = ? AND user_id = ?
                    ''', (message_id, user_id))
                else:
                    # Insert or update the rating
                    cursor.execute('''
                    INSERT INTO message_ratings (message_id, user_id, session_id, rating)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(message_id, user_id) DO UPDATE SET rating = excluded.rating
                    ''', (message_id, user_id, session_id, rating))
                
                conn.commit()
                return True
            except sqlite3.Error as e:
                conn.rollback()
                logger.error(f"Error updating message rating: {str(e)}")
                return False
            finally:
                cursor.close()

    def get_message_rating(self, message_id: str, user_id: str) -> str | None:
        """Get the rating of a message"""
        with self.db_lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                SELECT rating
                FROM message_ratings
                WHERE message_id = ? AND user_id = ?
                ''', (message_id, user_id))
                
                result = cursor.fetchone()
                return result['rating'] if result else None
            except sqlite3.Error as e:
                logger.error(f"Error getting message rating: {str(e)}")
                return None
            finally:
                cursor.close()