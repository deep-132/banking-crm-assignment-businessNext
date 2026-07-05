Feature: Personal loan outreach discovery
  As a Relationship Manager
  I want to find high-value customers likely to convert for a personal loan
  So that I can send them a personalized, approvable outreach message

  Background:
    Given the CRM database is seeded with synthetic customers, accounts,
      transactions, products held, loan offers, and interactions
    And the RM has an active chat session with no prior result set

  # --- full_search ---------------------------------------------------------

  Scenario: RM discovers high-value customers likely to convert
    Given the RM has not searched for anything yet in this session
    When the RM asks "Find high-value customers likely to convert for a
      personal loan this month and generate personalized WhatsApp messages"
    Then the system retrieves eligible customers who do not already hold an
      active personal loan
    And each candidate receives a high-value score based on balance, income,
      tenure, and product depth
    And each candidate receives a conversion score based on salary
      regularity, recent large spending, loan inquiry history, credit score
      band, and existing debt load
    And each candidate is matched to the best loan tier they qualify for,
      with a recommended amount and rate
    And the top-ranked candidates are returned with a generated WhatsApp
      draft grounded only in that customer's own fact sheet
    And the full scored candidate universe is cached for this session

  Scenario: No customer qualifies
    Given every retrieved candidate fails eligibility for the requested
      product
    When the RM asks the system to find candidates for that product
    Then the system reports that no eligible customers were found
    And suggests widening the city or segment filter
    And does not fabricate a result

  # --- refine ---------------------------------------------------------------

  Scenario: RM narrows an existing result set
    Given a full_search has already produced a cached scored universe in
      this session
    When the RM asks "Just show me the top 5 in Mumbai"
    Then the system re-ranks and re-filters the cached universe only
    And does not re-query the database or recompute any score
    And returns at most 5 customers, all located in Mumbai

  # --- explain ----------------------------------------------------------------

  Scenario: RM asks why a customer was selected
    Given a full_search has already produced a cached scored universe
      containing that customer
    When the RM asks "Why was <customer> picked?"
    Then the system returns the exact scoring breakdown already computed for
      that customer
    And makes no additional LLM call to answer

  Scenario: RM asks to explain a customer with no prior search
    Given no full_search has been run yet in this session
    When the RM asks the system to explain a customer
    Then the system asks a clarifying question instead of guessing
    And does not invent a customer or a scoring rationale

  # --- clarify ----------------------------------------------------------------

  Scenario: RM's request is ambiguous
    Given the RM's message does not contain enough information to choose a
      route confidently
    When the router cannot resolve an action
    Then the system asks one specific clarifying question
    And takes no other action until the RM responds

  # --- grounding constraint (applies to every WhatsApp draft) ---------------

  Scenario: Generated outreach never invents facts
    Given a customer has been scored, matched to a product, and shortlisted
    When the system drafts a WhatsApp message for that customer
    Then the message only references facts present in that customer's fact
      sheet (name, recommended product, amount, one real conversion signal)
    And the message does not include a fabricated phone number, link, or
      unverified claim
    And if the generation call fails, a deterministic fallback template is
      used instead of leaving the field empty
