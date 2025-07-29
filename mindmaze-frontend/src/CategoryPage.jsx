import React, { useState } from 'react';
import './CategoryPage.css';
import { Calculator, BookOpen, Globe, Lightbulb, Brain, Zap, Trophy, ArrowLeft, Target, PartyPopper, Music, Film, Gamepad2, Microscope, Palette, Map, ChefHat, Stethoscope, Code, Camera, Leaf } from 'lucide-react';

const CategoryPage = ({ onSelectCategory, onBackToHome, user }) => {
  const [selectedCategory, setSelectedCategory] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const categories = [
    {
      id: 'very_basic_math',
      name: 'Math Level-1',
      icon: Calculator,
      description: 'Simple arithmetic and number puzzles',
      color: 'from-blue-500 to-blue-600',
      difficulty: 'Easy'
    },
    {
      id: 'Oral_math',
      name: 'Math Level-2',
      icon: Brain,
      description: 'Oral Calculations',
      color: 'from-purple-500 to-purple-600',
      difficulty: 'Hard'
    },
    {
      id: 'social_science',
      name: 'Social Science',
      icon: Globe,
      description: 'History, geography, and culture',
      color: 'from-green-500 to-green-600',
      difficulty: 'Medium'
    },
    {
      id: 'general_knowledge',
      name: 'General Knowledge',
      icon: BookOpen,
      description: 'Random facts and trivia',
      color: 'from-orange-500 to-orange-600',
      difficulty: 'Medium'
    },
    {
      id: 'riddles',
      name: 'Brain Teasers',
      icon: Lightbulb,
      description: 'Logic puzzles and riddles',
      color: 'from-yellow-500 to-yellow-600',
      difficulty: 'Medium'
    },
    {
      id: 'word_games',
      name: 'Word Games',
      icon: Zap,
      description: 'Vocabulary and language puzzles',
      color: 'from-teal-500 to-teal-600',
      difficulty: 'Easy'
    },
    {
      id: 'movies',
      name: 'Movies & TV',
      icon: Film,
      description: 'Entertainment and cinema trivia',
      color: 'from-red-500 to-red-600',
      difficulty: 'Easy'
    },
    {
      id: 'music',
      name: 'Music',
      icon: Music,
      description: 'Songs, artists, and music theory',
      color: 'from-pink-500 to-pink-600',
      difficulty: 'Easy'
    },
    {
      id: 'gaming',
      name: 'Gaming',
      icon: Gamepad2,
      description: 'Video games and gaming culture',
      color: 'from-indigo-500 to-indigo-600',
      difficulty: 'Medium'
    },
    {
      id: 'funny',
      name: 'Fun & Random',
      icon: PartyPopper,
      description: 'Silly questions and weird facts',
      color: 'from-emerald-500 to-emerald-600',
      difficulty: 'Easy'
    },
    {
      id: 'science',
      name: 'Science',
      icon: Microscope,
      description: 'Physics, chemistry, and biology challenges',
      color: 'from-cyan-500 to-cyan-600',
      difficulty: 'Hard'
    },
    {
      id: 'art',
      name: 'Art & Design',
      icon: Palette,
      description: 'Art history, styles, and techniques',
      color: 'from-rose-500 to-rose-600',
      difficulty: 'Medium'
    },
    {
      id: 'travel',
      name: 'Travel & Adventure',
      icon: Map,
      description: 'World destinations and travel trivia',
      color: 'from-amber-500 to-amber-600',
      difficulty: 'Easy'
    },
    {
      id: 'cooking',
      name: 'Cooking & Cuisine',
      icon: ChefHat,
      description: 'Recipes, cuisines, and culinary facts',
      color: 'from-lime-500 to-lime-600',
      difficulty: 'Medium'
    },
    {
      id: 'health',
      name: 'Health & Medicine',
      icon: Stethoscope,
      description: 'Medical facts and wellness trivia',
      color: 'from-violet-500 to-violet-600',
      difficulty: 'Hard'
    },
    {
      id: 'programming',
      name: 'Programming',
      icon: Code,
      description: 'Coding concepts and tech trivia',
      color: 'from-blue-600 to-blue-700',
      difficulty: 'Hard'
    },
    {
      id: 'photography',
      name: 'Photography',
      icon: Camera,
      description: 'Camera techniques and photo history',
      color: 'from-gray-500 to-gray-600',
      difficulty: 'Medium'
    },
    {
      id: 'nature',
      name: 'Nature & Wildlife',
      icon: Leaf,
      description: 'Plants, animals, and ecosystems',
      color: 'from-green-600 to-green-700',
      difficulty: 'Medium'
    }
  ];

  const handleCategorySelect = (category) => {
    setSelectedCategory(category.id);
    setIsLoading(true);
    
    // Simulate brief loading before starting match
    setTimeout(() => {
      onSelectCategory(category);
      setIsLoading(false);
    }, 500);
  };

  const getDifficultyColor = (difficulty) => {
    switch(difficulty) {
      case 'Easy': return 'text-green-400';
      case 'Medium': return 'text-yellow-400';
      case 'Hard': return 'text-red-400';
      default: return 'text-gray-400';
    }
  };

  return (
    <div className="category-page">
      <div className="category-header">
        <button className="back-button" onClick={onBackToHome}>
          <ArrowLeft size={20} />
          <span>Back to Home</span>
        </button>
        
        <div className="category-title">
          <h1>Choose Your Battle Category</h1>
          <p>Select a category to find opponents and start battling!</p>
        </div>

        <div className="user-info-small">
          <span>{user.username}</span>
          <span className="score">{user.score || 0} pts</span>
        </div>
      </div>

      <div className="categories-grid">
        {categories.map((category) => {
          const IconComponent = category.icon;
          const isSelected = selectedCategory === category.id;
          const isCurrentLoading = isLoading && isSelected;

          return (
            <div 
              key={category.id}
              className={`category-card ${isSelected ? 'selected' : ''} ${isCurrentLoading ? 'loading' : ''}`}
              onClick={() => !isLoading && handleCategorySelect(category)}
            >
              <div className={`category-icon bg-gradient-to-r ${category.color}`}>
                {isCurrentLoading ? (
                  <div className="loading-spinner">⟳</div>
                ) : (
                  <IconComponent size={32} />
                )}
              </div>
              
              <div className="category-content">
                <h3 className="category-name">{category.name}</h3>
                <p className="category-description">{category.description}</p>
                
                <div className="category-meta">
                  <span className={`difficulty ${getDifficultyColor(category.difficulty)}`}>
                    <Target size={14} />
                    {category.difficulty}
                  </span>
                </div>
              </div>

              {isSelected && (
                <div className="selection-indicator">
                  <Trophy size={20} />
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="category-footer">
        <p className="category-hint">
          💡 Choose wisely! Each category has different types of challenges and opponents.
        </p>
      </div>
    </div>
  );
};

export default CategoryPage;