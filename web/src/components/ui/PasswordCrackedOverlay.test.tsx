import { test, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/react';
import { PasswordCrackedOverlay } from './PasswordCrackedOverlay';

test('closes on Escape', async () => {
    const handleClose = vi.fn();
    render(<PasswordCrackedOverlay show={true} password="test" onClose={handleClose} />);

    // Press Escape
    fireEvent.keyDown(window, { key: 'Escape', code: 'Escape' });

    expect(handleClose).toHaveBeenCalled();
});
