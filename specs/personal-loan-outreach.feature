Feature: Personal loan outreach discovery
  As a Relationship Manager
  I want to find high-value customers likely to convert for a personal loan
  So that I can send them a personalized, approvable outreach message

  Background:
    Given the CRM database is seeded with synthetic customers, accounts, transactions, products held, loan offers, and interactions

  # --- full_search ---------------------------------------------------------

  Scenario: RM discovers high-value customers likely to convert
    Given the RM has not searched for anything yet in this session
    When the RM asks to find high-value customers likely to convert for a personal loan and generate WhatsApp messages
    Then the system returns a scored, ranked list of eligible customers
    And every returned customer excludes anyone who already holds an active personal loan
    And every returned customer has a high-value score and a conversion score
    And every returned customer is matched to a recommended loan product and amount
    And every returned customer has a generated WhatsApp draft
    And the full scored candidate universe is cached for this session

  Scenario: No customer qualifies
    Given every retrieved candidate fails eligibility for the requested product
    When the RM asks the system to find candidates for that product
    Then the system reports that no eligible customers were found
    And the system does not fabricate a result

  # --- refine ----------------------------------------------------------------

  Scenario: RM narrows an existing result set
    Given a full_search has already produced a cached scored universe in this session
    When the RM asks to narrow the results to a specific city and a smaller count
    Then the system re-ranks and re-filters the cached universe only
    And the system does not recompute the scored universe
    And the number of returned customers does not exceed the requested count

  # --- explain -----------------------------------------------------------------

  Scenario: RM asks why a customer was selected
    Given a full_search has already produced a cached scored universe in this session
    When the RM asks why that specific customer was selected
    Then the system returns the exact scoring breakdown already computed for that customer
    And the system makes no additional LLM call to answer

  Scenario: RM asks to explain a customer with no prior search
    Given no full_search has been run yet in this session
    When the RM asks the system to explain a customer
    Then the system asks a clarifying question instead of guessing
    And the system does not invent a customer or a scoring rationale

  # --- clarify -----------------------------------------------------------------

  Scenario: RM's request is ambiguous
    Given the RM's message does not contain enough information to choose a route confidently
    When the router cannot resolve an action
    Then the system asks one specific clarifying question
    And the system takes no other action until the RM responds

  # --- grounding constraint (applies to every WhatsApp draft) ----------------

  Scenario: Generated outreach never invents facts
    Given a customer has been scored, matched to a product, and shortlisted
    When the system drafts a WhatsApp message for that customer
    Then the message only references facts present in that customer's fact sheet
    And the message does not include a fabricated phone number or link
    And a deterministic fallback template is used if the generation call fails
