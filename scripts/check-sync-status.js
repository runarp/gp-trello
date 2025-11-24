#!/usr/bin/env node

/**
 * Check sync status - find cards that need to be synced
 * Updated to work with data/ folder structure
 */

const fs = require('fs');
const path = require('path');

function sanitizeFileName(name) {
  if (!name || typeof name !== 'string') return 'untitled';
  return name
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-+|-+$/g, '')
    .substring(0, 100) || 'untitled';
}

function findSyncedCards(dataDir = 'data') {
  const synced = [];
  
  if (!fs.existsSync(dataDir)) {
    return synced;
  }

  // Find all board directories
  const boards = fs.readdirSync(dataDir, { withFileTypes: true })
    .filter(dirent => dirent.isDirectory())
    .map(dirent => dirent.name);

  for (const boardDir of boards) {
    const boardPath = path.join(dataDir, boardDir);
    
    // Find all list directories in this board
    const lists = fs.readdirSync(boardPath, { withFileTypes: true })
      .filter(dirent => dirent.isDirectory())
      .map(dirent => dirent.name);

    for (const listDir of lists) {
      const listPath = path.join(boardPath, listDir);
      const files = fs.readdirSync(listPath)
        .filter(f => f.endsWith('.md') && f !== '.index.json');
      
      for (const file of files) {
        const cardName = file.replace('.md', '');
        synced.push({
          board: boardDir,
          list: listDir,
          card: cardName,
          file: path.join(listPath, file)
        });
      }
    }
  }

  return synced;
}

function main() {
  const dataDir = process.argv[2] || 'data';
  const synced = findSyncedCards(dataDir);
  
  // Group by board
  const byBoard = {};
  for (const card of synced) {
    if (!byBoard[card.board]) {
      byBoard[card.board] = [];
    }
    byBoard[card.board].push(card);
  }
  
  console.log(`Found ${synced.length} synced cards in ${dataDir}/:\n`);
  
  for (const [board, cards] of Object.entries(byBoard)) {
    console.log(`\n${board} (${cards.length} cards):`);
    for (const card of cards) {
      console.log(`  ✓ ${card.list}/${card.card}.md`);
    }
  }
  
  console.log(`\nTotal: ${synced.length} cards synced across ${Object.keys(byBoard).length} board(s)`);
}

if (require.main === module) {
  main();
}

module.exports = { findSyncedCards, sanitizeFileName };

