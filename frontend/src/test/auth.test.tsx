import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider, useAuth } from '../context/AuthContext';
import { LoginPage } from '../pages/LoginPage';
import { api } from '../lib/api';

vi.mock('../lib/api', () => ({
  api: {
    auth: {
      login: vi.fn(),
      logout: vi.fn(),
      me: vi.fn(),
    },
  },
  getCsrfToken: vi.fn(() => 'mock-csrf-token'),
}));

const TestConsumer: React.FC = () => {
  const { user, loading, logout } = useAuth();
  if (loading) return <div>Loading Auth...</div>;
  if (!user) return <div>Unauthenticated</div>;
  return (
    <div>
      <div>Authenticated as {user.name} ({user.role})</div>
      <button onClick={logout}>Log Out</button>
    </div>
  );
};

describe('AuthContext and LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('restores authenticated user on mount without touching localStorage', async () => {
    const mockUser = {
      id: 'user-123',
      name: 'Sarah Chen',
      email: 'sarah.payments@newtonite.internal',
      role: 'USER',
      is_active: true,
      teams: [{ team_id: 't-1', team_name: 'Payments', team_role: 'APPROVER' }],
    };
    (api.auth.me as any).mockResolvedValue(mockUser);

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    expect(screen.getByText('Loading Auth...')).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText('Authenticated as Sarah Chen (USER)')).toBeInTheDocument();
    });
    expect(api.auth.me).toHaveBeenCalled();
  });

  it('submits login form and updates authenticated state via HttpOnly cookie flow', async () => {
    (api.auth.me as any).mockRejectedValue(new Error('Unauthenticated'));
    const mockUser = {
      id: 'user-456',
      name: 'Alex Admin',
      email: 'admin@newtonite.internal',
      role: 'ADMIN',
      is_active: true,
      teams: [],
    };
    (api.auth.login as any).mockResolvedValue({ user: mockUser });

    render(
      <BrowserRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/name@newtonite\.internal/i)).toBeInTheDocument();
    });

    fireEvent.change(screen.getByPlaceholderText(/name@newtonite\.internal/i), {
      target: { value: 'admin@newtonite.internal' },
    });
    const passwordInputs = screen.getAllByDisplayValue('');
    const passwordInput = passwordInputs.find((input) => (input as HTMLInputElement).type === 'password');
    if (passwordInput) {
      fireEvent.change(passwordInput, { target: { value: 'SecretPassword123!' } });
    }

    const submitBtn = screen.getByRole('button', { name: /sign in/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(api.auth.login).toHaveBeenCalledWith('admin@newtonite.internal', 'SecretPassword123!');
    });
  });

  it('handles logout and clears local auth state', async () => {
    const mockUser = {
      id: 'user-123',
      name: 'Sarah Chen',
      email: 'sarah.payments@newtonite.internal',
      role: 'USER',
      is_active: true,
      teams: [],
    };
    (api.auth.me as any).mockResolvedValue(mockUser);
    (api.auth.logout as any).mockResolvedValue({});

    render(
      <AuthProvider>
        <TestConsumer />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Authenticated as Sarah Chen (USER)')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Log Out'));

    await waitFor(() => {
      expect(screen.getByText('Unauthenticated')).toBeInTheDocument();
    });
    expect(api.auth.logout).toHaveBeenCalled();
  });
});

