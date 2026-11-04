import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Header } from '../components/common/Header';
import { Navbar } from '../components/common/Navbar';
import { OnboardingScreen } from '../components/screens/OnboardingScreen';

describe('Accessibility & Semantic HTML Compliance Tests', () => {
  it('Header includes landmark role banner and descriptive aria-labels', () => {
    render(
      <Header
        currentFieldId="field-kolar-001"
        onOpenFieldSelect={vi.fn()}
        lang="en"
        onToggleLang={vi.fn()}
        isOnline={true}
      />
    );

    const banner = screen.getByRole('banner');
    expect(banner).toBeInTheDocument();

    const switchLangBtn = screen.getByRole('button', { name: /switch language to ಕನ್ನಡ/i });
    expect(switchLangBtn).toHaveAttribute('aria-label');
  });

  it('Navbar adheres to tablist/tab accessibility patterns with labels', () => {
    render(
      <Navbar
        activeScreen="overview"
        onSelectScreen={vi.fn()}
        lang="en"
        unreadAlertsCount={0}
        pendingAdvisoriesCount={0}
      />
    );

    const nav = screen.getByRole('navigation', { name: /main farmer navigation/i });
    expect(nav).toBeInTheDocument();

    const tabs = screen.getAllByRole('tab');
    expect(tabs.length).toBe(5);
    tabs.forEach((tab) => {
      expect(tab).toHaveAttribute('aria-selected');
    });
  });

  it('OnboardingScreen defines labeled landmark region and explicit form inputs', () => {
    render(
      <OnboardingScreen
        onCompleteOnboarding={vi.fn()}
        lang="en"
        onToggleLang={vi.fn()}
      />
    );

    const region = screen.getByRole('region', { name: /agrikafka farmer advisory/i });
    expect(region).toBeInTheDocument();

    const select = screen.getByRole('combobox');
    expect(select).toBeInTheDocument();
  });
});

