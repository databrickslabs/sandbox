import React, { useState, useRef, useEffect } from 'react';
import styled from 'styled-components';
import { useChat } from '../context/ChatContext';
import databricksLogo from '../assets/images/databricks_icon.svg';
import databricksText from '../assets/images/databricks_text.svg';
import { fetchUserInfo } from '../api/chatApi';

const UserMenuContainer = styled.div`
  position: relative;
`;

const Avatar = styled.button`
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #434A93;
  color: white;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
`;

const MenuDropdown = styled.div<{ isOpen: boolean }>`
  display: ${props => props.isOpen ? 'flex' : 'none'};
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 8px;
  width: 240px;
  background: #F6F7F9;
  box-shadow: 0px 4px 8px rgba(27, 49, 57, 0.04);
  border-radius: 2px;
  border: 1px solid #D1D9E1;
  flex-direction: column;
  z-index: 100;
`;

const UserInfo = styled.div`
  padding: 10px;
  color: #5F7281;
  font-size: 13px;
  line-height: 16px;
  border-bottom: 1px solid #D1D9E1;
  margin: 4px 2px;
`;

const MenuItem = styled.button`
  margin: 2px;
  width: 100%;
  padding: 10px;
  text-align: left;
  background: none;
  border: none;
  font-size: 12px;
  color: #11171C;
  cursor: pointer;
  line-height: 20px;

  &:hover {
    background: rgba(0, 0, 0, 0.04);
  }
`;

const LogoContainer = styled.div`
  padding-left: 8px;
  height: 32px;
  min-heigh:32px;
  margin-top: 4px;
`;

const LogoIcon = styled.img`
  height: 22px;
`;

const LogoText = styled.img`
  height: 22px;
  margin-left: 4px;
`;

const UserMenu: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const { logout } = useChat();
  const [userInfo, setUserInfo] = useState<{username: string, email: string, displayName: string} | null>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    const getUserInfo = async () => {
      try {
        const userInfo = await fetchUserInfo();
        setUserInfo(userInfo);
      } catch (error) {
        console.error('Failed to fetch user info:', error);
      }
    };
    getUserInfo();
  }, []);

  const handleLogout = () => {
    try {
      logout();
    } catch (error) {
      console.error('Failed to logout:', error);
    }
    setIsOpen(false);
  };

  if(!userInfo) {
    return null;
  }

  return (
    <>
     <LogoContainer data-testid="logo-container">
        <LogoIcon src={databricksLogo} alt="Databricks Logo" data-testid="logo-icon"/>
        <LogoText src={databricksText} alt="Databricks" data-testid="logo-text"/>
      </LogoContainer>
      <UserMenuContainer ref={menuRef}>
        <Avatar onClick={() => setIsOpen(!isOpen)}>{userInfo.username.charAt(0).toUpperCase()}</Avatar>
        <MenuDropdown isOpen={isOpen}>
          <UserInfo>
            {userInfo.displayName}<br />
            <span style={{fontSize: '12px', color: '#5F7281', display: 'block', marginTop: '2px'}}>{userInfo.email}</span>
          </UserInfo>
          <MenuItem onClick={handleLogout}>Log out</MenuItem>
        </MenuDropdown>
      </UserMenuContainer>
    </>
  );
};

export default UserMenu; 