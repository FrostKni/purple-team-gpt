import { useState } from 'react';
import {
  Brain,
  Star,
  TrendingUp,
  Lightbulb,
  MessageSquare,
  Save,
  Download,
  Upload,
  RefreshCw,
  Zap,
  Target,
  Shield,
  Sword,
  CheckCircle2,
  AlertCircle,
  BarChart3,
  LineChart,
  PieChart
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Progress } from './ui/progress';
import { ScrollArea } from './ui/scroll-area';
import { cn } from '../lib/utils';

interface LearningDashboardProps {
  sessionId: string | null;
  findings: any[];
}

interface LearningPattern {
  id: string;
  type: 'attack' | 'defense';
  pattern: string;
  success_rate: number;
  usage_count: number;
  last_used: string;
  source: 'automatic' | 'human_feedback';
}

interface FeedbackItem {
  id: string;
  agent: 'red' | 'blue';
  action: string;
  result: string;
  rating: number | null;
  feedback: string;
  timestamp: string;
}

// Mock data
const mockPatterns: LearningPattern[] = [
  { id: '1', type: 'attack', pattern: 'SQL injection via error-based payload', success_rate: 85, usage_count: 23, last_used: '2h ago', source: 'automatic' },
  { id: '2', type: 'attack', pattern: 'Nmap stealth scan with OS detection', success_rate: 92, usage_count: 45, last_used: '1h ago', source: 'human_feedback' },
  { id: '3', type: 'defense', pattern: 'Block IP after 3 failed SSH attempts', success_rate: 78, usage_count: 67, last_used: '30m ago', source: 'automatic' },
  { id: '4', type: 'defense', pattern: 'Alert on suspicious process creation', success_rate: 95, usage_count: 89, last_used: '15m ago', source: 'human_feedback' },
  { id: '5', type: 'attack', pattern: 'Directory traversal via encoded payload', success_rate: 67, usage_count: 12, last_used: '3h ago', source: 'automatic' },
];

const mockFeedback: FeedbackItem[] = [
  { id: '1', agent: 'red', action: 'Port scan on target', result: 'Found 3 open ports', rating: 5, feedback: 'Great scan coverage', timestamp: '10:30 AM' },
  { id: '2', agent: 'blue', action: 'Blocked suspicious IP', result: 'Attack mitigated', rating: 4, feedback: 'Quick response time', timestamp: '10:32 AM' },
  { id: '3', agent: 'red', action: 'SQLMap attack', result: 'Data extracted', rating: 3, feedback: 'Should try different technique', timestamp: '10:45 AM' },
];

export function LearningDashboard({ sessionId, findings }: LearningDashboardProps) {
  const [patterns, setPatterns] = useState<LearningPattern[]>(mockPatterns);
  const [feedbackItems, setFeedbackItems] = useState<FeedbackItem[]>(mockFeedback);
  const [selectedRating, setSelectedRating] = useState<number | null>(null);
  const [feedbackText, setFeedbackText] = useState('');
  const [activeTab, setActiveTab] = useState<'patterns' | 'feedback' | 'export'>('patterns');

  const attackPatterns = patterns.filter(p => p.type === 'attack');
  const defensePatterns = patterns.filter(p => p.type === 'defense');
  const avgSuccessRate = patterns.reduce((acc, p) => acc + p.success_rate, 0) / patterns.length;
  const totalUsage = patterns.reduce((acc, p) => acc + p.usage_count, 0);
  const humanPatterns = patterns.filter(p => p.source === 'human_feedback').length;

  const handleRating = (feedbackId: string, rating: number) => {
    setFeedbackItems(prev => prev.map(f => 
      f.id === feedbackId ? { ...f, rating } : f
    ));
  };

  const exportToJsonl = () => {
    const highRatedFeedback = feedbackItems.filter(f => f.rating && f.rating >= 4);
    const jsonl = highRatedFeedback.map(f => JSON.stringify({
      prompt: f.action,
      completion: f.result,
      rating: f.rating,
      feedback: f.feedback,
    })).join('\n');
    
    const blob = new Blob([jsonl], { type: 'application/jsonl' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'purple_team_training.jsonl';
    a.click();
  };

  return (
    <div className="h-full flex flex-col gap-4 p-4 overflow-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold bg-gradient-to-r from-green-400 to-emerald-400 bg-clip-text text-transparent">
            Learning & Feedback Center
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            Improve agent performance through human feedback and pattern analysis
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" className="gap-2">
            <RefreshCw className="h-4 w-4" />
            Sync Memory
          </Button>
          <Button onClick={exportToJsonl} className="gap-2 bg-gradient-to-r from-green-600 to-emerald-600">
            <Download className="h-4 w-4" />
            Export JSONL
          </Button>
        </div>
      </div>

      {/* Learning Stats */}
      <div className="grid grid-cols-5 gap-4">
        <Card className="bg-gradient-to-br from-green-500/10 to-transparent border-green-500/20">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground uppercase tracking-wider">Patterns Learned</p>
                <p className="text-3xl font-bold text-green-400 mt-1">{patterns.length}</p>
              </div>
              <Brain className="h-8 w-8 text-green-500/30" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-blue-500/10 to-transparent border-blue-500/20">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground uppercase tracking-wider">Avg Success Rate</p>
                <p className="text-3xl font-bold text-blue-400 mt-1">{avgSuccessRate.toFixed(0)}%</p>
              </div>
              <TrendingUp className="h-8 w-8 text-blue-500/30" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-purple-500/10 to-transparent border-purple-500/20">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground uppercase tracking-wider">Total Usage</p>
                <p className="text-3xl font-bold text-purple-400 mt-1">{totalUsage}</p>
              </div>
              <Zap className="h-8 w-8 text-purple-500/30" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-yellow-500/10 to-transparent border-yellow-500/20">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground uppercase tracking-wider">Human Feedback</p>
                <p className="text-3xl font-bold text-yellow-400 mt-1">{humanPatterns}</p>
              </div>
              <MessageSquare className="h-8 w-8 text-yellow-500/30" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-pink-500/10 to-transparent border-pink-500/20">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground uppercase tracking-wider">Feedback Items</p>
                <p className="text-3xl font-bold text-pink-400 mt-1">{feedbackItems.length}</p>
              </div>
              <Star className="h-8 w-8 text-pink-500/30" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-gray-500/20 pb-2">
        <Button
          variant={activeTab === 'patterns' ? 'default' : 'ghost'}
          size="sm"
          onClick={() => setActiveTab('patterns')}
          className={cn(activeTab === 'patterns' && "bg-gradient-to-r from-green-600 to-emerald-600")}
        >
          <Brain className="h-4 w-4 mr-2" />
          Learned Patterns
        </Button>
        <Button
          variant={activeTab === 'feedback' ? 'default' : 'ghost'}
          size="sm"
          onClick={() => setActiveTab('feedback')}
          className={cn(activeTab === 'feedback' && "bg-gradient-to-r from-green-600 to-emerald-600")}
        >
          <MessageSquare className="h-4 w-4 mr-2" />
          Feedback Portal
        </Button>
        <Button
          variant={activeTab === 'export' ? 'default' : 'ghost'}
          size="sm"
          onClick={() => setActiveTab('export')}
          className={cn(activeTab === 'export' && "bg-gradient-to-r from-green-600 to-emerald-600")}
        >
          <Download className="h-4 w-4 mr-2" />
          Export & Train
        </Button>
      </div>

      {/* Main Content */}
      <div className="flex-1 grid grid-cols-3 gap-4 min-h-0">
        {/* Left Column - Patterns/Feedback List */}
        <Card className="flex flex-col col-span-2">
          <CardContent className="flex-1 min-h-0 p-4">
            {activeTab === 'patterns' && (
              <ScrollArea className="h-full">
                <div className="space-y-4">
                  {/* Attack Patterns */}
                  <div>
                    <h3 className="text-sm font-medium flex items-center gap-2 mb-3">
                      <Sword className="h-4 w-4 text-red-400" />
                      Attack Patterns ({attackPatterns.length})
                    </h3>
                    <div className="space-y-2">
                      {attackPatterns.map((pattern) => (
                        <div
                          key={pattern.id}
                          className="p-3 rounded-lg border border-red-500/20 bg-red-500/5 hover:bg-red-500/10 transition-colors"
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex-1">
                              <p className="text-sm font-medium">{pattern.pattern}</p>
                              <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                                <span className="flex items-center gap-1">
                                  <CheckCircle2 className="h-3 w-3 text-green-400" />
                                  {pattern.success_rate}% success
                                </span>
                                <span>Used {pattern.usage_count}x</span>
                                <span>{pattern.last_used}</span>
                              </div>
                            </div>
                            <Badge 
                              variant={pattern.source === 'human_feedback' ? 'success' : 'secondary'}
                              className="text-[10px]"
                            >
                              {pattern.source === 'human_feedback' ? 'Human' : 'Auto'}
                            </Badge>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Defense Patterns */}
                  <div>
                    <h3 className="text-sm font-medium flex items-center gap-2 mb-3">
                      <Shield className="h-4 w-4 text-blue-400" />
                      Defense Patterns ({defensePatterns.length})
                    </h3>
                    <div className="space-y-2">
                      {defensePatterns.map((pattern) => (
                        <div
                          key={pattern.id}
                          className="p-3 rounded-lg border border-blue-500/20 bg-blue-500/5 hover:bg-blue-500/10 transition-colors"
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex-1">
                              <p className="text-sm font-medium">{pattern.pattern}</p>
                              <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                                <span className="flex items-center gap-1">
                                  <CheckCircle2 className="h-3 w-3 text-green-400" />
                                  {pattern.success_rate}% success
                                </span>
                                <span>Used {pattern.usage_count}x</span>
                                <span>{pattern.last_used}</span>
                              </div>
                            </div>
                            <Badge 
                              variant={pattern.source === 'human_feedback' ? 'success' : 'secondary'}
                              className="text-[10px]"
                            >
                              {pattern.source === 'human_feedback' ? 'Human' : 'Auto'}
                            </Badge>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </ScrollArea>
            )}

            {activeTab === 'feedback' && (
              <ScrollArea className="h-full">
                <div className="space-y-3">
                  {feedbackItems.map((item) => (
                    <div
                      key={item.id}
                      className={cn(
                        "p-4 rounded-lg border",
                        item.agent === 'red' ? "border-red-500/20 bg-red-500/5" : "border-blue-500/20 bg-blue-500/5"
                      )}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-3">
                          <div className={cn(
                            "p-2 rounded-lg",
                            item.agent === 'red' ? "bg-red-500/20" : "bg-blue-500/20"
                          )}>
                            {item.agent === 'red' ? (
                              <Sword className="h-4 w-4 text-red-400" />
                            ) : (
                              <Shield className="h-4 w-4 text-blue-400" />
                            )}
                          </div>
                          <div>
                            <p className="text-sm font-medium">{item.action}</p>
                            <p className="text-xs text-muted-foreground">{item.result}</p>
                            <p className="text-[10px] text-muted-foreground mt-1">{item.timestamp}</p>
                          </div>
                        </div>
                        
                        {/* Star Rating */}
                        <div className="flex items-center gap-1">
                          {[1, 2, 3, 4, 5].map((star) => (
                            <button
                              key={star}
                              onClick={() => handleRating(item.id, star)}
                              className="focus:outline-none"
                            >
                              <Star
                                className={cn(
                                  "h-5 w-5 transition-colors",
                                  item.rating && star <= item.rating
                                    ? "text-yellow-400 fill-yellow-400"
                                    : "text-gray-500 hover:text-yellow-300"
                                )}
                              />
                            </button>
                          ))}
                        </div>
                      </div>
                      
                      {item.feedback && (
                        <div className="mt-3 pt-3 border-t border-gray-500/10">
                          <p className="text-xs text-muted-foreground">
                            <MessageSquare className="h-3 w-3 inline mr-1" />
                            {item.feedback}
                          </p>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </ScrollArea>
            )}

            {activeTab === 'export' && (
              <div className="h-full flex flex-col items-center justify-center text-center">
                <div className="w-24 h-24 mx-auto mb-4 rounded-full bg-gradient-to-br from-green-500/20 to-emerald-500/20 flex items-center justify-center">
                  <Download className="h-12 w-12 text-green-400/50" />
                </div>
                <h3 className="text-lg font-semibold mb-2">Export Training Data</h3>
                <p className="text-sm text-muted-foreground mb-6 max-w-md">
                  Export high-quality feedback as JSONL for fine-tuning your custom model.
                  Only items with 4+ star ratings are included.
                </p>
                
                <div className="grid grid-cols-2 gap-4 w-full max-w-sm">
                  <Card className="p-4">
                    <p className="text-2xl font-bold text-green-400">
                      {feedbackItems.filter(f => f.rating && f.rating >= 4).length}
                    </p>
                    <p className="text-xs text-muted-foreground">Items to Export</p>
                  </Card>
                  <Card className="p-4">
                    <p className="text-2xl font-bold text-blue-400">{patterns.length}</p>
                    <p className="text-xs text-muted-foreground">Patterns</p>
                  </Card>
                </div>

                <div className="flex items-center gap-3 mt-6">
                  <Button variant="outline" className="gap-2">
                    <Upload className="h-4 w-4" />
                    Import Feedback
                  </Button>
                  <Button onClick={exportToJsonl} className="gap-2 bg-gradient-to-r from-green-600 to-emerald-600">
                    <Download className="h-4 w-4" />
                    Export JSONL
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Right Column - Stats & Quick Feedback */}
        <div className="flex flex-col gap-4">
          {/* Quick Stats */}
          <Card className="p-4">
            <h3 className="text-sm font-medium mb-3 flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-purple-400" />
              Learning Progress
            </h3>
            <div className="space-y-3">
              <div>
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="text-muted-foreground">Attack Pattern Accuracy</span>
                  <span className="text-green-400">87%</span>
                </div>
                <Progress value={87} className="h-2" />
              </div>
              <div>
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="text-muted-foreground">Defense Response Time</span>
                  <span className="text-blue-400">92%</span>
                </div>
                <Progress value={92} className="h-2" />
              </div>
              <div>
                <div className="flex items-center justify-between text-xs mb-1">
                  <span className="text-muted-foreground">Human Feedback Quality</span>
                  <span className="text-yellow-400">78%</span>
                </div>
                <Progress value={78} className="h-2" />
              </div>
            </div>
          </Card>

          {/* Quick Feedback Form */}
          <Card className="p-4 flex-1">
            <h3 className="text-sm font-medium mb-3 flex items-center gap-2">
              <Lightbulb className="h-4 w-4 text-yellow-400" />
              Purple Instructions
            </h3>
            <p className="text-xs text-muted-foreground mb-3">
              Provide custom guidance for agents to improve their strategies.
            </p>
            <textarea
              value={feedbackText}
              onChange={(e) => setFeedbackText(e.target.value)}
              placeholder="e.g., 'Use a different bypass for this WAF' or 'Check for XXE vulnerabilities first'"
              className="w-full h-32 p-3 rounded-lg bg-black/20 border border-gray-500/20 text-sm resize-none focus:outline-none focus:border-green-500/50"
            />
            <Button className="w-full mt-3 gap-2 bg-gradient-to-r from-green-600 to-emerald-600">
              <Save className="h-4 w-4" />
              Save Instruction
            </Button>
          </Card>
        </div>
      </div>
    </div>
  );
}