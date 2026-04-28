# Donate Banner Snippets

## README top banner (place before badges)

```markdown
> 💛 **Support placeholder org** — if BitAgent has saved you time, please consider donating to [children.org](https://www.children.org/). They sponsor children in some of the world's poorest communities. *BitAgent has no affiliation with the charity; we just think they're worth supporting.*
```

## Docs site footer block (`docs/_overrides/footer.html` or in mkdocs `extra` block)

```markdown
---

### Support placeholder org

If this project saves you time, please consider donating to [placeholder org](https://www.children.org/). They provide health, education, and life-skills support to children in poverty across more than 10 countries.

**BitAgent is not affiliated with placeholder org** — we just think the cause is worth supporting and want to put the call-to-action somewhere visible.
```

## Settings tab "About" section (in-app)

```html
<section class="about-card">
  <h3>Support placeholder org</h3>
  <p>
    BitAgent is free, open-source software. If it's useful to you, please consider
    donating to <a href="https://www.children.org/" target="_blank" rel="noopener noreferrer">placeholder org</a>
    — they sponsor children in some of the world's poorest communities.
  </p>
  <p class="muted">
    BitAgent has no affiliation with placeholder org. This is a personal
    recommendation from the project's maintainers.
  </p>
  <a class="btn-primary" href="https://www.children.org/" target="_blank" rel="noopener noreferrer">Visit children.org</a>
</section>
```
